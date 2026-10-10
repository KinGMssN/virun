/* Team's Supabase Google-auth wiring, adapted for separate pages.
   Preserved logic: PKCE flow, session restore, ?code callback handling. */
(function () {
  'use strict';
  var V = window.Virun;
  var supabaseClient = null, authInitPromise = null;

  function initSupabaseAuth() {
    if (authInitPromise) return authInitPromise;
    authInitPromise = (async function () {
      if (!window.supabase || !window.supabase.createClient)
        throw new Error('Supabase Auth client did not load. Check your internet connection and retry.');
      var response = await fetch('/api/auth/config', { headers: { 'Accept': 'application/json' } }),
        config = await response.json().catch(function () { return {}; });
      if (!response.ok) throw new Error(config.detail || 'Authentication is not configured on the backend.');
      supabaseClient = window.supabase.createClient(config.url, config.anon_key,
        { auth: { flowType: 'pkce', detectSessionInUrl: true, persistSession: true, autoRefreshToken: true } });
      supabaseClient.auth.onAuthStateChange(function (event, session) {
        if (session && session.user) {
          V.store.set('username',
            (session.user.user_metadata && session.user.user_metadata.full_name) || session.user.email || 'Traveler');
          if (event === 'SIGNED_IN' && new URLSearchParams(location.search).has('code'))
            finishGoogleCallback(session);
        }
      });
      var result = await supabaseClient.auth.getSession();
      if (result.error) throw result.error;
      if (new URLSearchParams(location.search).has('code')) {
        if (!result.data.session)
          throw new Error('Google returned an authorization code, but Supabase did not create a session. Check the OAuth callback configuration.');
        finishGoogleCallback(result.data.session);
      }
      return supabaseClient;
    })();
    return authInitPromise;
  }

  function finishGoogleCallback(session) {
    if (session && session.user)
      V.store.set('username',
        (session.user.user_metadata && session.user.user_metadata.full_name) || session.user.email || 'Traveler');
    history.replaceState({}, document.title, location.pathname);
    if (!/journey-search\.html$/.test(location.pathname)) location.href = 'journey-search.html';
  }

  async function startGoogleSignIn(button, hint) {
    if (button) button.disabled = true;
    if (hint) { hint.style.display = 'block'; hint.textContent = 'Connecting to Google?'; }
    try {
      var client = await initSupabaseAuth(),
        redirectTo = location.origin + location.pathname;
      var result = await client.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: redirectTo, queryParams: { access_type: 'offline', prompt: 'select_account' } }
      });
      if (result.error) throw result.error;
    } catch (error) {
      if (hint) hint.textContent = error.message || 'Google sign-in could not start. Check Supabase Auth configuration.';
      if (button) button.disabled = false;
    }
  }

  if (new URLSearchParams(location.search).has('code')) {
    initSupabaseAuth().catch(function (err) {
      var hint = document.getElementById('googleHint') || document.getElementById('googleSignupHint');
      if (hint) { hint.style.display = 'block'; hint.textContent = err.message; }
    });
  }

  window.VirunAuth = { startGoogleSignIn: startGoogleSignIn, initSupabaseAuth: initSupabaseAuth };
})();
