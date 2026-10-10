/* Ask Virun panel — injected markup plus all behaviors.
   The team's trip-planner block (Groq /api calls) is preserved verbatim below. */
(function () {
  'use strict';
  document.body.insertAdjacentHTML('beforeend',
    '<button id="bot" class="bot" aria-label="Open Virun travel chat"><span class="bot-bob"><img id="botFace" class="bot-face" alt=""></span></button>' +
    '<aside id="botPanel" class="bot-panel" aria-label="Virun travel chat">' +
    '<div class="bot-panel-head"><img id="botAvatar" class="bot-panel-avatar" alt="Virun mascot"><div><h2>Ask Virun</h2><p id="botStatus">Choose a quick question.</p></div></div>' +
    '<div class="chips">' +
    '<button class="chip" data-reply="Choose a city in Explore, then pick it in Choose My Trip to theme the whole experience.">What do you want to explore?</button>' +
    '<button class="chip" data-reply="Open Train and Bus from the dashboard to compare mock train and bus options for your route.">Plan a train or bus journey</button>' +
    '<button class="chip" data-reply="Trip payments move in three visible stages: advance to confirm, balance held during the trip, release after completion.">How does trip protection work?</button>' +
    '<button class="chip" data-reply="Pack for the weather and planned activities. Keep identity documents, water and a power bank easy to reach.">What should I pack?</button>' +
    '</div>' +
    '<div class="voice-row"><button class="voice-btn" id="voiceBtn" type="button" aria-label="Ask Virun with your voice"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg><span>Ask with voice</span></button><span class="voice-hint" id="voiceHint"></span></div>' +
    '<form class="type-row" id="typeForm"><input id="typeInput" placeholder="Type your question..." autocomplete="off" aria-label="Type your question"><button class="btn small" type="submit">Send</button></form>' +
    '<div id="botReply" class="bot-reply" aria-live="polite"></div></aside>');
})();
(function(){'use strict';
var form=document.getElementById('typeForm'),input=document.getElementById('typeInput'),reply=document.getElementById('botReply'),status=document.getElementById('botStatus');
if(!form||!input||!reply||!status)return;
var daysField=document.createElement('div'),daysInput=document.createElement('input'),daysLabel=document.createElement('label'),pendingTrip='';
daysField.className='field';
daysField.hidden=true;
daysLabel.htmlFor='tripDurationDays';
daysLabel.textContent='Days at destination (1–15)';
daysInput.id='tripDurationDays';
daysInput.type='number';
daysInput.min='1';
daysInput.max='15';
daysInput.step='1';
daysInput.setAttribute('aria-label','Days at destination');
daysField.appendChild(daysLabel);
daysField.appendChild(daysInput);
form.insertBefore(daysField,form.querySelector('button[type="submit"]'));
async function postJson(url,body,label){
var response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),data;
try{data=await response.json()}catch(error){throw new Error(label+' returned an unreadable response.')}
if(!response.ok){var detail=data.detail;if(detail&&typeof detail==='object')detail=detail.message||detail.code||JSON.stringify(detail);throw new Error((detail||label+' failed')+' [HTTP '+response.status+']')}
return data
}
document.addEventListener('submit',function(event){
if(event.target!==form)return;
var question=input.value.trim(),tripRequest=/\b(plan|itinerary|trip|travel|vacation|holiday)\b/i.test(question)||!!pendingTrip;
if(!tripRequest)return;
event.preventDefault();
event.stopImmediatePropagation();
var statedDays=question.match(/\b(\d{1,2})\s*(?:days?|nights?)\b/i);
if(statedDays&&!daysInput.value)daysInput.value=statedDays[1];
var days=Number(daysInput.value);
if(!Number.isInteger(days)||days<1||days>15){
pendingTrip=pendingTrip?pendingTrip+' '+question:question;
input.value='';
daysField.hidden=false;
daysInput.focus();
reply.textContent='How many days would you like to spend at the destination? Choose 1–15 days, then send your trip request again.';
reply.classList.add('show');
reply.style.whiteSpace='pre-line';
status.textContent='Trip duration is required (1–15 days).';
return
}
var original=pendingTrip?pendingTrip+' '+question:question;
pendingTrip='';
input.value='';
daysField.hidden=true;
daysInput.value='';
reply.textContent='Understanding your trip request...';
reply.classList.add('show');
reply.style.whiteSpace='pre-line';
status.textContent='Parsing the trip with Groq.';
(async function(){
var dateParts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()),dateValues={};
dateParts.forEach(function(part){if(part.type!=='literal')dateValues[part.type]=part.value});
var parsed=await postJson('/api/parse-trip',{message:original+' [trip-days: '+days+']',timezone:'Asia/Kolkata',reference_date:dateValues.year+'-'+dateValues.month+'-'+dateValues.day},'Trip parser');
if(parsed.status==='needs_clarification'){var questions=(parsed.clarification_questions||[]).join(' ');pendingTrip=original;reply.textContent='A few details are needed: '+questions;status.textContent='Reply with the missing trip details.';return}
if(parsed.status!=='ready'||!parsed.trip_request){var code=parsed.error_code;if(code==='NOT_CONFIGURED')throw new Error('Groq is not configured in Render. Add GROQ_API_KEY to the service environment and redeploy.');if(code==='QUOTA_EXCEEDED')throw new Error('The Groq account has reached its request limit. Check Groq API usage.');if(code==='MODEL_TIMEOUT')throw new Error('Groq took too long to respond. Please retry.');throw new Error(code||'Groq could not understand the trip request.')}
var trip=parsed.trip_request,planRequest=Object.assign({},trip);
if(planRequest.ac_preference==='no_preference')planRequest.ac_preference='none';
if(planRequest.priority==='comfort')planRequest.priority='balanced';
status.textContent='Checking transport routes and generating your itinerary with Groq.';
var routePromise=postJson('/api/plan',planRequest,'Transport planner').then(function(plan){
if(!Array.isArray(plan.itineraries)||!plan.itineraries.length)return 'No feasible transport routes were found in the current dataset.';
return plan.itineraries.map(function(item){return item.label+' | INR '+item.total_fare_inr}).join('\n')
}).catch(function(error){return 'Transport routes unavailable: '+error.message});
var itineraryPromise=postJson('/api/generate-itinerary',{destination:trip.destination,duration_days:trip.duration_days,preferences:original},'Groq itinerary generator');
var results=await Promise.all([routePromise,itineraryPromise]),itinerary=results[1],lines=['Transport route options (simulated):',results[0],'','AI-generated '+itinerary.duration_days+'-day sightseeing suggestions for '+itinerary.destination+' (verify details before travel):'];
itinerary.days.forEach(function(day){lines.push('','Day '+day.day+': '+day.title,'Morning: '+day.morning,'Afternoon: '+day.afternoon,'Evening: '+day.evening)});
reply.textContent=lines.join('\n');
status.textContent='Transport routes and day-by-day itinerary are ready.'
})().catch(function(error){reply.textContent='Could not create your trip plan: '+error.message;status.textContent='The request needs attention.'})
},true);
})();
(function () {
  'use strict';
  var V = window.Virun, imageAsset = V.imageAsset;
  var bot = document.getElementById('bot'), panel = document.getElementById('botPanel'),
    botFace = document.getElementById('botFace'), botAvatar = document.getElementById('botAvatar'),
    botStatus = document.getElementById('botStatus'), botTimer = null;
  botFace.src = imageAsset('chatbot/virun-happy.png');
  botAvatar.src = imageAsset('chatbot/virun-cute.png');
  bot.addEventListener('click', function () {
    var opening = !panel.classList.contains('open');
    panel.classList.toggle('open');
    if (opening) {
      botFace.src = imageAsset('chatbot/virun-sleepy.png');
      botAvatar.src = imageAsset('chatbot/virun-cute.png');
      botStatus.textContent = 'Choose a quick question.';
      clearTimeout(botTimer);
      botTimer = setTimeout(function () { botFace.src = imageAsset('chatbot/virun-happy.png'); }, 650);
    }
  });
  document.querySelectorAll('.chip').forEach(function (b) {
    b.addEventListener('click', function () {
      var r = document.getElementById('botReply');
      botFace.src = imageAsset('chatbot/virun-glitch.png');
      botAvatar.src = imageAsset('chatbot/virun-glitch.png');
      botStatus.textContent = 'Thinking...';
      r.classList.remove('show');
      clearTimeout(botTimer);
      botTimer = setTimeout(function () {
        r.textContent = b.getAttribute('data-reply');
        r.classList.add('show');
        botFace.src = imageAsset('chatbot/virun-cool.png');
        botAvatar.src = imageAsset('chatbot/virun-cool.png');
        botStatus.textContent = 'Here is a clear next step.';
      }, 420);
    });
  });
  var voiceBtn = document.getElementById('voiceBtn'), voiceHint = document.getElementById('voiceHint');
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  function voiceAnswer(q) {
    var t = q.toLowerCase(), ans;
    if (/guide/.test(t)) ans = 'Guides manage their own profiles, previous works and tour examples in the guide dashboard.';
    else if (/pack|carry|bring/.test(t)) ans = 'Pack for the weather and planned activities. Keep identity documents, water and a power bank easy to reach.';
    else if (/plan|itinerary|trip|\bday\b/.test(t)) ans = 'Pick your city in Choose My Trip, then use Train and Bus on the dashboard to plan the journey.';
    else if (/book|price|cost|payment|rs\b/.test(t)) ans = 'Sample pricing: Single Trip Rs 100, Two Trips Rs 200, Three Trips Rs 300, Frequent Rs 500. The booking flow shows advance, held balance and release steps.';
    else if (/weather|rain|temperature/.test(t)) ans = 'Every destination card shows live weather from Open-Meteo. Check the badge on the city you are eyeing.';
    else if (/hello|hi\b|hey/.test(t)) ans = 'Hello! Ask me about packing, trip planning, booking, payment or weather.';
    else ans = 'I heard: \u201c' + q + '\u201d. For now I answer best from the quick questions above \u2014 full voice answers arrive with the backend.';
    return ans;
  }
  if (voiceBtn) {
    if (!SR) { voiceBtn.style.display = 'none'; }
    else {
      voiceBtn.addEventListener('click', function () {
        var rec = new SR();
        rec.lang = 'en-IN'; rec.interimResults = false; rec.maxAlternatives = 1;
        voiceBtn.classList.add('listening');
        botStatus.textContent = 'Listening... speak now.';
        voiceHint.textContent = '';
        rec.onresult = function (e) {
          var q = e.results[0][0].transcript;
          voiceBtn.classList.remove('listening');
          botFace.src = imageAsset('chatbot/virun-cute.png');
          botAvatar.src = imageAsset('chatbot/virun-cute.png');
          botStatus.textContent = 'You asked: \u201c' + q + '\u201d';
          var r = document.getElementById('botReply');
          r.classList.remove('show');
          clearTimeout(botTimer);
          botTimer = setTimeout(function () { r.textContent = voiceAnswer(q); r.classList.add('show'); }, 420);
        };
        rec.onerror = function () { voiceBtn.classList.remove('listening'); botStatus.textContent = 'Could not hear you. Try again.'; };
        rec.onend = function () { voiceBtn.classList.remove('listening'); };
        try { rec.start(); } catch (err) { voiceBtn.classList.remove('listening'); }
      });
    }
  }
  var typeForm = document.getElementById('typeForm');
  if (typeForm) {
    typeForm.addEventListener('submit', function (e) {
      var input = document.getElementById('typeInput'), q = input.value.trim();
      if (!q) return;
      if (/\b(plan|itinerary|trip|travel|vacation|holiday)\b/i.test(q)) return; /* handled by the trip planner */
      e.preventDefault();
      input.value = '';
      botFace.src = imageAsset('chatbot/virun-cute.png');
      botAvatar.src = imageAsset('chatbot/virun-cute.png');
      botStatus.textContent = 'You asked: \u201c' + q + '\u201d';
      var r = document.getElementById('botReply');
      r.classList.remove('show');
      clearTimeout(botTimer);
      botTimer = setTimeout(function () { r.textContent = voiceAnswer(q); r.classList.add('show'); }, 420);
    });
  }
})();
