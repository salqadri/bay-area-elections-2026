/* Google Places (New) official accessible widget; manual entry is always kept. */
(function(root) {
  'use strict';
  let loading;
  function load(key) {
    if (root.google?.maps?.importLibrary) return Promise.resolve();
    if (loading) return loading;
    loading = new Promise((resolve,reject)=>{
      const callback = '__tallGoogleReady';
      const script=document.createElement('script');
      let settled=false;
      const timeout=setTimeout(()=>finish(new Error('Google address suggestions took too long to load.')),12000);
      function finish(error) {
        if(settled)return;settled=true;clearTimeout(timeout);delete root[callback];
        error?reject(error):resolve();
      }
      root[callback]=()=>finish();
      script.onerror=()=>finish(new Error('Google address suggestions could not load.'));
      script.src='https://maps.googleapis.com/maps/api/js?'+new URLSearchParams({key,loading:'async',libraries:'places',v:'weekly',callback});
      script.async=true;document.head.append(script);
    });
    return loading;
  }
  async function attach({key,container,onSelect,onError}) {
    await load(key);
    const {PlaceAutocompleteElement}=await root.google.maps.importLibrary('places');
    const widget=new PlaceAutocompleteElement({includedRegionCodes:['us'],requestedRegion:'us',requestedLanguage:'en',locationBias:{north:38.9,south:36.8,east:-121.0,west:-123.6}});
    widget.setAttribute('aria-label','Home address');
    widget.setAttribute('placeholder','Start typing your home address');
    widget.addEventListener('gmp-select',async event=>{
      try {
        const place=event.placePrediction.toPlace();
        await place.fetchFields({fields:['formattedAddress']});
        if(!place.formattedAddress)throw new Error('Select a complete street address, or enter it manually.');
        onSelect(place.formattedAddress);
      } catch(error){onError(error);}
    });
    widget.addEventListener('gmp-error',()=>onError(new Error('Address suggestions are unavailable. Enter your address manually.')));
    container.replaceChildren(widget);
    return widget;
  }
  root.TallGoogleAutocomplete={attach};
})(globalThis);
