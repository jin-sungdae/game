// Opt-in document-start observer, installed before app scripts by LUMA_METADATA_AUDIT.
// No network, timers, rendering overrides or CSP exceptions. Bounded diagnostic storage.
(() => {
  const trace={version:1,fetchAttempts:0,xhrAttempts:0,manifestAttempts:0,cspViolations:0,resources:[],attempts:[]};
  let output;
  const publish=()=>{if(output)output.setAttribute('aria-label','LUMA_METADATA_AUDIT '+JSON.stringify(trace));};
  const urlOf=value=>typeof value==='string'?value:String(value?.url??value);
  const attempt=(kind,value)=>{
    const url=urlOf(value);trace[kind==='fetch'?'fetchAttempts':'xhrAttempts']++;
    if(/\/manifest\.json(?:[?#]|$)/.test(url))trace.manifestAttempts++;
    if(trace.attempts.length<100)trace.attempts.push({kind,url,time:performance.now()});publish();
  };
  const originalFetch=globalThis.fetch;
  globalThis.fetch=function(...args){attempt('fetch',args[0]);return Reflect.apply(originalFetch,this,args);};
  const originalOpen=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(...args){attempt('xhr',args[1]);return Reflect.apply(originalOpen,this,args);};
  addEventListener('securitypolicyviolation',event=>{trace.cspViolations++;if(trace.attempts.length<100)trace.attempts.push({kind:'csp',directive:event.effectiveDirective,url:event.blockedURI});publish();});
  const observer=new PerformanceObserver(list=>{
    for(const entry of list.getEntries())if(trace.resources.length<100)trace.resources.push({url:entry.name,initiator:entry.initiatorType,start:entry.startTime,duration:entry.duration});
    publish();
  });
  observer.observe({type:'resource',buffered:true});
  addEventListener('DOMContentLoaded',()=>{
    output=document.createElement('span');output.setAttribute('role','status');
    output.style.cssText='position:fixed;left:0;top:0;opacity:0;pointer-events:none;width:1px;height:1px';
    document.body.append(output);publish();
  },{once:true});
})();
