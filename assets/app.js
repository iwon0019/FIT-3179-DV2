'use strict';
(() => {
  const chartNames = ['01-national','02-residence','03-slope','04-location-map','05-heatmap','06-jitter','07-weather','08-radial','09-fire-timeline','10-state-map','11-hotspot-map','12-bin-map'];
  const views = new Map();
  let summary, selectedYear = 2025, weatherCity = 'L00', slopeCity = 'L00', settingYear = false, suppressBrush = false;
  const $ = id => document.getElementById(id);
  const load = async url => { const response = await fetch(url); if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`); return response.json(); };
  function textUpdates() {
    document.querySelectorAll('.selected-year').forEach(el => el.textContent = selectedYear);
    const ranked = summary.annual.filter(r => r.year === selectedYear).sort((a,b) => b.pm25 - a.pm25);
    $('location-insight').textContent = `${selectedYear}: ${ranked[0].city} ranks highest (${ranked[0].pm25.toFixed(2)} µg/m³). ${ranked.at(-1).city} ranks lowest (${ranked.at(-1).pm25.toFixed(2)} µg/m³). This comparison covers eight selected locations only.`;
    $('fire-insight').textContent = `Retained detections: ${summary.fireTotals['2024'].toLocaleString()} during 2024; ${summary.fireTotals['2025'].toLocaleString()} during 2025. Detection counts differ from counts of individual fires.`;
    document.querySelectorAll('.weather-city-name').forEach(el => el.textContent = summary.cities.find(c => c.key === weatherCity).name);
  }
  async function signal(id, key, value) { const v = views.get(id); if (v) await v.signal(key, value).runAsync(); }
  async function setEpisode(start, end, fromBrush = false) {
    const min = `${selectedYear}-01-01`, max = `${selectedYear}-12-31`;
    if (!start || !end || start > end || start < min || end > max) {
      $('episode-status').textContent = `Choose dates within ${selectedYear}. The start must precede or equal the end.`;
      return;
    }
    $('episode-start').value = start; $('episode-end').value = end;
    if (!fromBrush && views.has('09')) {
      suppressBrush = true;
      try { await views.get('09').change('episode_store',vega.changeset().remove(()=>true)).runAsync(); }
      finally { suppressBrush = false; }
    }
    await signal('11', 'episodeStart', start); await signal('11', 'episodeEnd', end);
    $('episode-status').textContent = `${start} to ${end} · ${fromBrush ? 'selected from the timeline' : 'episode map date range'}`;
  }
  function localDate(value) {
    const date = new Date(value);
    return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  }
  async function render(name) {
    const id = name.slice(0,2), container = $('chart-'+id);
    container.classList.add('loading');
    try {
      const spec = await load(`specs/${name}.json`);
      spec.width = Math.max(180, Math.floor(container.clientWidth));
      if (window.innerWidth < 500 && id === '06') spec.encoding.x.axis.labelAngle = -50;
      const result = await vegaEmbed(container, spec, {actions:false, renderer:'canvas', tooltip:{theme:'light'}, defaultStyle:false});
      views.set(id, result.view);
      if (id === '09') result.view.addSignalListener('episode', (_name, value) => {
        if (settingYear || suppressBrush) return;
        if (value && value.date) {
          const min = `${selectedYear}-01-01`, max = `${selectedYear}-12-31`;
          setEpisode([min,localDate(value.date[0])].sort().at(-1),[max,localDate(value.date[1])].sort()[0],true).catch(console.error);
        } else setEpisode(`${selectedYear}-01-01`,`${selectedYear}-12-31`,true).catch(console.error);
      });
      const resize = new ResizeObserver(entries => {
        const width = Math.floor(entries[0].contentRect.width);
        if (width > 0 && Math.abs(width - result.view.width()) > 2) result.view.width(width).resize().runAsync().catch(console.error);
      });
      resize.observe(container);
    } catch (error) {
      console.error(name,error);
      const p=document.createElement('p');p.className='error-message';p.textContent='This chart could not load. Refresh or inspect the linked chart specification.';container.replaceChildren(p);
    } finally { container.classList.remove('loading'); }
  }
  async function start() {
    summary = await load('data/site/summary.json');
    for (const city of summary.cities) {
      $('slope-city').add(new Option(city.name,city.key));
      if (city.weather) $('weather-city').add(new Option(city.name,city.key));
    }
    textUpdates();
    await Promise.all(chartNames.map(render));
    $('year').addEventListener('change',async event => {
      selectedYear = Number(event.target.value); settingYear = true;
      $('update-status').textContent='Updating…';
      try {
        await Promise.all(['04','05','06','07','08','09','10','11','12'].map(id=>signal(id,'selectedYear',selectedYear)));
        const timeline = views.get('09'); if(timeline) await timeline.change('episode_store',vega.changeset().remove(()=>true)).runAsync();
        for (const id of ['episode-start','episode-end']) { $(id).min=`${selectedYear}-01-01`;$(id).max=`${selectedYear}-12-31`; }
        await setEpisode(`${selectedYear}-01-01`,`${selectedYear}-12-31`);
        textUpdates();$('update-status').textContent=`${selectedYear} selected`;
      } catch (error) { console.error(error);$('update-status').textContent='Could not update all charts. Refresh to retry.'; }
      finally { settingYear = false; }
    });
    $('weather-city').addEventListener('change',async e=>{weatherCity=e.target.value;await Promise.all(['07','08'].map(id=>signal(id,'selectedCity',weatherCity)));textUpdates();});
    $('slope-city').addEventListener('change',async e=>{slopeCity=e.target.value;await signal('03','selectedCity',slopeCity);});
    for (const id of ['episode-start','episode-end']) $(id).addEventListener('change',()=>setEpisode($('episode-start').value,$('episode-end').value));
    $('reset-episode').addEventListener('click',async()=>{
      const timeline=views.get('09');if(timeline)await timeline.change('episode_store',vega.changeset().remove(()=>true)).runAsync();
      await setEpisode(`${selectedYear}-01-01`,`${selectedYear}-12-31`);
    });
    document.documentElement.dataset.chartsReady = String(views.size);
  }
  start().catch(error=>{console.error(error);$('update-status').textContent='Unable to load data. Please refresh.';});
})();
