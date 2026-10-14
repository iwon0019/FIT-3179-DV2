// Compile and execute the actual pinned Vega-Lite libraries against local data.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname,'..');
const warnings=[];
const context=vm.createContext({console:{log:console.log,warn:(...a)=>warnings.push(a.join(' ')),error:(...a)=>warnings.push(a.join(' '))},setTimeout,clearTimeout,performance,structuredClone});
for(const name of ['vega','vega-lite']) vm.runInContext(fs.readFileSync(path.join(root,'assets/vendor',name+'.min.js'),'utf8'),context);
const vega=context.vega, vl=context.vegaLite;
const loader={load:async url=>fs.promises.readFile(path.join(root,url),'utf8'),sanitize:async url=>({href:url})};
function marks(view){
  const found=[];
  function walk(item){if(item.mark?.role==='mark')found.push(item);for(const c of item.items||[])walk(c);}
  walk(view.scenegraph().root);return found;
}
(async()=>{
  const results=[];
  for(const name of fs.readdirSync(path.join(root,'specs')).filter(n=>n.endsWith('.json')).sort()){
    const spec=JSON.parse(fs.readFileSync(path.join(root,'specs',name),'utf8'));spec.width=600;
    const compiled=vl.compile(spec).spec;
    const view=new vega.View(vega.parse(compiled),{renderer:'none',loader}).initialize();
    await view.runAsync();
    const initial=marks(view);assert(initial.length>0,`${name} has no marks`);
    for(const mark of initial){for(const key of ['x','y','size','outerRadius'])if(typeof mark[key]==='number')assert(Number.isFinite(mark[key]),`${name}: nonfinite ${key}`);}
    if(spec.params?.some(p=>p.name==='selectedYear')){await view.signal('selectedYear',2024).runAsync();assert(marks(view).length>0);await view.signal('selectedYear',2025).runAsync();}
    if(name.startsWith('11')){
      const count=marks(view).filter(m=>m.mark.marktype==='symbol').length;
      assert.equal(count,4867,'Full-year hotspot count must match prepared 2025 data');
      await view.signal('episodeStart','2025-07-01').signal('episodeEnd','2025-07-31').runAsync();
      const filtered=marks(view).filter(m=>m.mark.marktype==='symbol').length;assert(filtered>0&&filtered<count,'Episode filter must narrow points');
    }
    if(name.startsWith('07')){assert.equal(initial.length,365);await view.signal('selectedCity','L07').runAsync();assert.equal(marks(view).length,365);}
    if(name.startsWith('08'))assert.equal(initial.filter(m=>m.mark.marktype==='arc').length,12);
    if(name.startsWith('04'))assert.equal(initial.filter(m=>m.mark.marktype==='symbol').length,8);
    if(name.startsWith('05'))assert.equal(initial.length,96);
    if(name.startsWith('06'))assert.equal(initial.length,8*365);
    results.push({spec:name,marks:initial.length,status:'pass'});view.finalize();
  }
  assert.equal(warnings.length,0,warnings.join('\n'));
  fs.mkdirSync(path.join(root,'output/qa'),{recursive:true});fs.writeFileSync(path.join(root,'output/qa/chart-checks.json'),JSON.stringify({results,warnings},null,2));
  console.log(JSON.stringify({charts:results.length,warnings,results},null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});

