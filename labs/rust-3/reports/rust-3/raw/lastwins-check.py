import sys,json,struct,collections
for p in sys.argv[1:]:
    b=open(p,'rb').read(); n=struct.unpack('<Q',b[:8])[0]; hdr=b[8:8+n]; data_len=len(b)-8-n
    pairs=[]
    def hook(ps): pairs.append(ps); return dict(ps)   # dict() = last wins (what serde_json HashMap does)
    try: last=json.loads(hdr,object_pairs_hook=hook)
    except Exception as e: print(p,"UNREADABLE",e); continue
    top=pairs[-1]; keys=[k for k,_ in top]; dups=[k for k,c in collections.Counter(keys).items() if c>1]
    # last-wins consistency: sizes match shape*dtype, offsets within data, contiguous non-overlapping
    sz={'BF16':2,'F16':2,'F32':4,'U8':1,'I8':1,'I64':8,'F64':8,'I32':4,'BOOL':1}
    ok=True; issues=[]
    ents=[(k,v) for k,v in last.items() if k!='__metadata__']
    offs=[]
    for k,v in ents:
        try:
            s,e=v['data_offsets']; numel=1
            for d in v['shape']: numel*=d
            if e-s!=numel*sz.get(v['dtype'],0): issues.append(f"size:{k}")
            if not(0<=s<=e<=data_len): issues.append(f"bounds:{k}")
            offs.append((s,e,k))
        except Exception as ex: issues.append(f"entry:{k}:{ex}")
    offs.sort()
    for (s1,e1,k1),(s2,e2,k2) in zip(offs,offs[1:]):
        if s2<e1: issues.append(f"overlap:{k1}/{k2}")
    if offs and offs[-1][1]!=data_len: issues.append("tail-gap")
    print(p.split('/')[-1],"dups=",len(dups),"last-wins:", "CONSISTENT" if not issues else "INCONSISTENT "+",".join(issues[:4]))
