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
/* Team's current chat protocol (AGENTIC AI 4.0): POST /api/chat {message, history} -> {reply}.
   Ported from their index.html sendToVirun; the old parse-trip/plan flow is retired. */
(function () {
  'use strict';
  var V = window.Virun, imageAsset = V.imageAsset;
  var form = document.getElementById('typeForm'), input = document.getElementById('typeInput'),
    reply = document.getElementById('botReply'), status = document.getElementById('botStatus');
  if (!form || !input || !reply || !status) return;
  var botFace = document.getElementById('botFace'), botAvatar = document.getElementById('botAvatar');
  var chatHistory = [], chatBusy = false;
  async function sendToVirun(question) {
    if (chatBusy) return;
    chatBusy = true;
    var sendButton = form.querySelector('button[type="submit"]');
    if (sendButton) sendButton.disabled = true;
    botFace.src = imageAsset('chatbot/virun-cute.png');
    botAvatar.src = imageAsset('chatbot/virun-cute.png');
    status.textContent = 'Virun is thinking...';
    reply.classList.remove('show');
    reply.textContent = '';
    try {
      var response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ message: question, history: chatHistory.slice(-8) })
      });
      var data = await response.json().catch(function () { return {}; });
      if (!response.ok) {
        var detail = data.detail;
        if (detail && typeof detail === 'object') detail = detail.message || detail.code;
        throw new Error(detail || 'Chat service returned HTTP ' + response.status);
      }
      if (!data || typeof data.reply !== 'string' || !data.reply.trim())
        throw new Error('Virun returned an empty reply. Please try again.');
      chatHistory.push({ role: 'user', content: question }, { role: 'assistant', content: data.reply.trim() });
      chatHistory = chatHistory.slice(-8);
      reply.textContent = data.reply.trim();
      reply.style.whiteSpace = 'pre-line';
      reply.classList.add('show');
      status.textContent = 'Answered by Virun AI.';
      botFace.src = imageAsset('chatbot/virun-happy.png');
      botAvatar.src = imageAsset('chatbot/virun-cute.png');
    } catch (error) {
      reply.textContent = error.message || 'Could not reach Virun. Check the connection and try again.';
      reply.classList.add('show');
      status.textContent = 'Chat needs attention.';
    } finally {
      chatBusy = false;
      if (sendButton) sendButton.disabled = false;
    }
  }
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var q = input.value.trim();
    if (!q || chatBusy) return;
    input.value = '';
    sendToVirun(q);
  });
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
})();