// node-side smoke of the browser (non-NODERAWFS) build: FS.writeFile + callMain
const fs=require('fs'),path=require('path');
const CIS2=require('./cis2_host.js');
const [wd,ids,n]=process.argv.slice(2);
(async()=>{
  const M=await CIS2({noInitialRun:true,print:s=>console.log(s),printErr:s=>console.error(s)});
  M.FS.mkdir('/weights');M.FS.mkdir('/ids');
  for(const f of ['config.json','model.safetensors','tokenizer.json'])M.FS.writeFile('/weights/'+f,fs.readFileSync(path.join(wd,f)));
  M.FS.writeFile('/ids/ids.txt',fs.readFileSync(ids));
  M.callMain(['--weights-dir','/weights','--ids','/ids/ids.txt','--gen-toks',n]);
})();
