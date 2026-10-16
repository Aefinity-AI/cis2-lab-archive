//! LLM-5b: streaming, per-tensor bf16 -> fp32 widening.
//!
//! Diagnosis (the double-hold this module fixes): the old load path in
//! `main.rs` (`std::fs::read(&weights_path)` into `raw`, then
//! `safetensors::SafeTensors::deserialize(&raw)`, then `load_f32_tensor`
//! per tensor) reads the WHOLE checkpoint file into one `Vec<u8>` and
//! keeps that `Vec<u8>` alive (as `raw`) for the entire load loop, while
//! simultaneously building up the full f32 model in a second set of
//! allocations (`embed_tokens`, each `LayerWeights`, `final_norm`,
//! `lm_head`). By the last tensor, both are resident at once: the whole
//! bf16 file (§3.5: bf16 is half the byte-width of f32) plus the whole f32
//! model, i.e. peak RSS approx. 1.5x the f32 model size (0.5x for the
//! still-held bf16 file + 1x for the finished f32 model), which is what
//! sent a 7B checkpoint (~28-30 GB f32-equivalent) to ~45 GB and past a
//! 31 GB Kaggle CPU kernel's RAM (tests/kaggle/LLM4-LOG.md, OOM during
//! "loading + widening weights").
//!
//! This module never holds more than one tensor's raw bf16 bytes at a
//! time: it reads only the safetensors header up front (a few KB-MB of
//! JSON, not the multi-GB data section), then for each tensor seeks
//! directly to that tensor's byte range on disk, reads exactly those
//! bytes into a function-local buffer, widens them, and returns the
//! f32 `Vec` -- the local raw buffer is dropped when the function
//! returns. Peak RSS is therefore approx. the f32 model built so far plus
//! (at most) one tensor's raw bf16 bytes, not the whole file.
//!
//! Bit-exactness: the widening arithmetic itself (`crate::math::widen_bf16`,
//! §3.5's exact zero-extending bit-shift) and the byte order / element
//! order it is applied in (`raw[2*i]`, `raw[2*i+1]` little-endian pair per
//! element, ascending `i`) are copied verbatim from the old
//! `load_f32_tensor` in `main.rs`. Nothing about the arithmetic changes --
//! only where the source bytes come from (one seek+read per tensor
//! instead of one read of the whole file up front).

use crate::math::widen_bf16;
use std::collections::HashMap;
use std::io::{Read, Seek, SeekFrom};

/// One tensor's entry from the safetensors header: dtype string (as
/// written in the JSON, e.g. "BF16"), shape, and its byte range within the
/// data section (relative to the first byte after the header, i.e. after
/// the 8-byte length prefix + the header JSON itself).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TensorEntry {
    pub dtype: String,
    pub shape: Vec<usize>,
    pub data_offsets: (u64, u64),
}

/// Parses a safetensors header JSON blob (the `n` bytes immediately after
/// the 8-byte little-endian header-length prefix, per the safetensors file
/// format) into a name -> `TensorEntry` map. Pure function: touches no
/// file, no data-section bytes, ignores the optional `__metadata__` key.
pub fn parse_header(header_json: &[u8]) -> HashMap<String, TensorEntry> {
    let v: serde_json::Value =
        serde_json::from_slice(header_json).expect("safetensors header is not valid JSON");
    let mut out = HashMap::new();
    let obj = v.as_object().expect("safetensors header is not a JSON object");
    for (name, entry) in obj {
        if name == "__metadata__" {
            continue;
        }
        let dtype = entry["dtype"]
            .as_str()
            .unwrap_or_else(|| panic!("tensor {name}: missing/invalid dtype"))
            .to_string();
        let shape: Vec<usize> = entry["shape"]
            .as_array()
            .unwrap_or_else(|| panic!("tensor {name}: missing shape"))
            .iter()
            .map(|x| x.as_u64().expect("shape entry not an integer") as usize)
            .collect();
        let offs = entry["data_offsets"]
            .as_array()
            .unwrap_or_else(|| panic!("tensor {name}: missing data_offsets"));
        assert_eq!(offs.len(), 2, "tensor {name}: data_offsets is not a 2-tuple");
        let s = offs[0].as_u64().expect("data_offsets[0] not an integer");
        let e = offs[1].as_u64().expect("data_offsets[1] not an integer");
        out.insert(
            name.clone(),
            TensorEntry {
                dtype,
                shape,
                data_offsets: (s, e),
            },
        );
    }
    out
}

/// Reads the 8-byte header-length prefix and the header JSON from
/// `reader` (leaving the reader positioned at the start of the data
/// section) and returns the parsed tensor index plus the absolute
/// data-section start offset (bytes from the start of the file/stream).
/// Never reads any tensor's data bytes.
pub fn read_index<R: Read>(reader: &mut R) -> (HashMap<String, TensorEntry>, u64) {
    let mut len_buf = [0u8; 8];
    reader
        .read_exact(&mut len_buf)
        .expect("read safetensors 8-byte header length prefix");
    let n = u64::from_le_bytes(len_buf);
    let mut header_buf = vec![0u8; n as usize];
    reader
        .read_exact(&mut header_buf)
        .expect("read safetensors header JSON");
    (parse_header(&header_buf), 8 + n)
}

/// Streams exactly one tensor's raw bf16 bytes (seek + read_exact; no
/// other tensor's bytes are touched, and no other tensor's bytes are ever
/// resident because of this call) and widens them to f32 via the same
/// exact bit-shift (`widen_bf16`, §3.5) and the same left-to-right element
/// order as the old whole-buffer `load_f32_tensor` in `main.rs`. The raw
/// byte buffer is local to this call and is dropped on return.
pub fn load_tensor_streaming<R: Read + Seek>(
    reader: &mut R,
    data_start: u64,
    index: &HashMap<String, TensorEntry>,
    name: &str,
    expect_shape: &[usize],
) -> Vec<f32> {
    let entry = index
        .get(name)
        .unwrap_or_else(|| panic!("tensor {name} missing"));
    assert_eq!(
        entry.shape, expect_shape,
        "tensor {name} shape mismatch"
    );
    // Same refusal as the old load_f32_tensor: a non-bf16 checkpoint whose
    // shapes happen to match must not be silently read as bf16 garbage.
    assert_eq!(
        entry.dtype, "BF16",
        "tensor {name} dtype {:?} is not BF16; CIS-2 pins bf16-on-disk weights (\u{00a7}3.5)",
        entry.dtype
    );
    let (s, e) = entry.data_offsets;
    assert!(e >= s, "tensor {name} has inverted data_offsets");
    let len = (e - s) as usize;
    assert_eq!(len % 2, 0, "bf16 tensor {name} has odd byte length");
    reader
        .seek(SeekFrom::Start(data_start + s))
        .unwrap_or_else(|err| panic!("seek to tensor {name}: {err}"));
    let mut raw = vec![0u8; len];
    reader
        .read_exact(&mut raw)
        .unwrap_or_else(|err| panic!("read tensor {name}: {err}"));
    let n = len / 2;
    let mut out = vec![0.0f32; n];
    for i in 0..n {
        let lo = raw[2 * i];
        let hi = raw[2 * i + 1];
        let bits = u16::from_le_bytes([lo, hi]);
        out[i] = widen_bf16(bits);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::whole_buffer_widen::load_f32_tensor_whole_buffer;
    use std::io::Cursor;

    /// Builds a minimal, real safetensors byte buffer (same format the
    /// production loader reads) holding a handful of BF16 tensors of
    /// varying shapes, using the `safetensors` crate's own serializer so
    /// the test buffer is byte-for-byte what a real checkpoint looks like.
    fn build_fixture() -> (Vec<(String, Vec<usize>, Vec<u16>)>, Vec<u8>) {
        // (name, shape, bf16 bit patterns in row-major order)
        let specs: Vec<(String, Vec<usize>, Vec<u16>)> = vec![
            (
                "model.embed_tokens.weight".to_string(),
                vec![4usize, 3usize],
                (0u16..12).map(|i| 0x3F80u16.wrapping_add(i * 7)).collect(),
            ),
            (
                "model.layers.0.input_layernorm.weight".to_string(),
                vec![5usize],
                vec![0x0000, 0x8000, 0x3F80, 0xBF80, 0x7F80], // incl. +0/-0/1/-1/+inf
            ),
            (
                "model.norm.weight".to_string(),
                vec![2usize, 2usize],
                vec![0x4049, 0xC049, 0x0001, 0x8001], // incl. smallest denormals
            ),
        ];

        let mut tensor_views: Vec<(String, safetensors::tensor::TensorView)> = Vec::new();
        let mut byte_bufs: Vec<Vec<u8>> = Vec::new();
        for (_, shape, bits) in &specs {
            let mut bytes = Vec::with_capacity(bits.len() * 2);
            for b in bits {
                bytes.extend_from_slice(&b.to_le_bytes());
            }
            byte_bufs.push(bytes);
            let _ = shape;
        }
        for (i, (name, shape, _)) in specs.iter().enumerate() {
            let view = safetensors::tensor::TensorView::new(
                safetensors::Dtype::BF16,
                shape.clone(),
                &byte_bufs[i],
            )
            .unwrap();
            tensor_views.push((name.clone(), view));
        }
        let buf = safetensors::tensor::serialize(tensor_views.iter().map(|(n, v)| (n.clone(), v)), None)
            .expect("serialize fixture safetensors buffer");
        (specs, buf)
    }

    #[test]
    fn streaming_matches_whole_buffer_bit_for_bit() {
        let (specs, buf) = build_fixture();

        // Old path: full buffer held, safetensors::SafeTensors view over it.
        let st = safetensors::SafeTensors::deserialize(&buf).unwrap();

        // New path: header-only parse + per-tensor seek/read from a Cursor
        // standing in for a file.
        let mut cursor = Cursor::new(buf.clone());
        let (index, data_start) = read_index(&mut cursor);

        for (name, shape, _bits) in &specs {
            let old = load_f32_tensor_whole_buffer(&st, name, shape);
            let new = load_tensor_streaming(&mut cursor, data_start, &index, name, shape);
            assert_eq!(
                old, new,
                "tensor {name}: streaming widen diverged from whole-buffer widen"
            );
            // Also compare raw bytes (belt-and-suspenders vs. any float
            // equality surprises with NaN/-0.0, though none are in this
            // fixture): bit-identical, not just PartialEq-equal.
            let old_bits: Vec<u32> = old.iter().map(|f| f.to_bits()).collect();
            let new_bits: Vec<u32> = new.iter().map(|f| f.to_bits()).collect();
            assert_eq!(old_bits, new_bits, "tensor {name}: differing bit patterns");
        }
    }

    #[test]
    fn parse_header_ignores_metadata_key() {
        let json = br#"{"__metadata__":{"format":"pt"},"t":{"dtype":"BF16","shape":[2],"data_offsets":[0,4]}}"#;
        let idx = parse_header(json);
        assert_eq!(idx.len(), 1);
        assert!(idx.contains_key("t"));
        assert!(!idx.contains_key("__metadata__"));
    }
}
