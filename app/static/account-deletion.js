/* Public deletion verification. Request capabilities live only in this page's memory. */
(function () {
  'use strict';
  const byId = (id) => document.getElementById(id);
  const status = byId('deletion-status');
  const error = byId('deletion-error');
  const providers = byId('deletion-providers');
  const buttons = Array.from(providers.querySelectorAll('[data-provider]'));
  const pending = byId('deletion-pending');
  const form = byId('deletion-confirm');
  const consent = byId('deletion-consent');
  const submit = byId('deletion-submit');
  const receipt = byId('deletion-receipt');
  const receiptCheck = byId('deletion-check-status');
  const retry = byId('deletion-retry');
  const restart = byId('deletion-restart');
  let available = [];
  let request = null;
  let timer = null;
  let generation = 0;
  let busy = false;
  let retryAction = null;

  function showError(message, action) {
    error.textContent = message;
    error.hidden = false;
    retryAction = action;
    retry.hidden = !action;
  }

  function clearError() {
    error.hidden = true;
    error.textContent = '';
    retry.hidden = true;
    retryAction = null;
  }

  function updateButtons() {
    buttons.forEach((button) => {
      const configured = available.includes(button.dataset.provider);
      button.disabled = busy || Boolean(request) || !configured;
      button.title = configured ? '' : 'This verification method is currently unavailable.';
    });
    submit.disabled = busy || !consent.checked || !request || request.status !== 'verified';
    receiptCheck.disabled = busy || !request || request.status !== 'submitted';
  }

  async function api(path, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch('/api/account-deletion/' + path, {
        method: body ? 'POST' : 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok || data.ok !== true) {
        const code = String(data.error || data.code || data.detail || '');
        const failure = new Error('request_failed');
        failure.code = code;
        failure.status = response.status;
        throw failure;
      }
      return data;
    } finally {
      clearTimeout(timeout);
    }
  }

  function failureMessage(failure) {
    if (failure.status === 429) return 'Too many attempts. Wait a little and retry.';
    if (failure.status === 410 || /expired/i.test(failure.code || '')) return 'Verification expired. Choose a sign-in method and verify again.';
    if (/not_linked|account_not_found|identity_not_found/i.test(failure.code || '')) return 'This sign-in identity is not linked to an HSK AI account. Choose the identity you already use in HSK AI.';
    return 'We could not complete this step. Your deletion request has not been confirmed. Retry or contact support.';
  }

  function reset() {
    generation += 1;
    clearTimeout(timer);
    request = null;
    busy = false;
    pending.hidden = true;
    form.hidden = true;
    receipt.hidden = true;
    receiptCheck.hidden = true;
    restart.hidden = true;
    consent.checked = false;
    byId('deletion-verification-link').removeAttribute('href');
    byId('deletion-account').textContent = '';
    clearError();
    status.textContent = 'Choose a sign-in method already linked to your account.';
    updateButtons();
  }

  async function loadProviders() {
    clearError();
    status.textContent = 'Loading available verification methods…';
    try {
      const data = await api('providers');
      available = Array.isArray(data.providers) ? data.providers : [];
      providers.hidden = false;
      status.textContent = available.length ? 'Choose a sign-in method already linked to your account.' : 'Verification is temporarily unavailable. Retry or contact support.';
      if (!available.length) showError('No verification methods are available right now.', loadProviders);
      updateButtons();
    } catch (failure) {
      status.textContent = 'Available verification methods could not be loaded.';
      showError(failureMessage(failure), loadProviders);
    }
  }

  function verificationUrl(provider, value) {
    const url = new URL(value);
    const hosts = { google: 'accounts.google.com', apple: 'appleid.apple.com', telegram: 't.me' };
    if (url.protocol !== 'https:' || url.hostname !== hosts[provider] || url.username || url.password) throw new Error('invalid_verification_url');
    return url.href;
  }

  function requestBody() {
    return { request_id: request.request_id, secret: request.secret };
  }

  function showReceipt(data) {
    clearTimeout(timer);
    clearError();
    pending.hidden = true;
    form.hidden = true;
    restart.hidden = true;
    receipt.hidden = false;
    status.textContent = data.status === 'completed' ? 'Your account deletion has been completed.' : 'Your deletion request has been received.';
    byId('receipt-title').textContent = data.status === 'completed' ? 'Account deletion completed' : 'Deletion request received';
    byId('deletion-receipt-message').textContent = data.status === 'completed' ? 'Your account data has been deleted according to the retention rules below.' : 'Your request has been saved. No account data is deleted immediately.';
    byId('deletion-reference').textContent = String(data.request_id || request.request_id);
    byId('deletion-requested-at').textContent = dateLabel(data.requested_at);
    byId('deletion-due-at').textContent = dateLabel(data.due_at);
    const completedAt = byId('deletion-completed-at');
    completedAt.hidden = data.status !== 'completed';
    completedAt.textContent = data.completed_at ? 'Completed: ' + dateLabel(data.completed_at) : '';
    receiptCheck.hidden = data.status !== 'submitted';
    // Keep the proof only in this page's memory for explicit receipt status checks.
    if (data.status === 'completed') request = { status: data.status };
    else request.status = data.status;
    updateButtons();
  }

  async function checkReceiptStatus() {
    if (busy || !request || request.status !== 'submitted') return;
    const current = generation;
    busy = true;
    clearError();
    updateButtons();
    try {
      const data = await api('status', requestBody());
      if (current !== generation) return;
      if (data.status !== 'submitted' && data.status !== 'completed') throw new Error('unexpected_status');
      showReceipt(data);
    } catch (failure) {
      if (current !== generation) return;
      showError('We could not check your request status. Your saved request remains submitted. Retry or contact support with your request reference.', checkReceiptStatus);
    } finally {
      if (current === generation) { busy = false; updateButtons(); }
    }
  }

  function dateLabel(value) {
    if (!value) return 'Contact support with your request reference.';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 'Contact support with your request reference.' : date.toLocaleString();
  }

  async function checkStatus() {
    clearTimeout(timer);
    const current = generation;
    if (!request || request.status !== 'pending') return;
    if (Date.now() >= request.expiresAt) {
      reset();
      showError('Verification expired. Choose a sign-in method and verify again.');
      return;
    }
    try {
      const data = await api('status', requestBody());
      if (current !== generation) return;
      if (data.status === 'verified') {
        if (typeof data.account_label !== 'string' || !data.account_label.trim()) throw new Error('missing_account');
        request.status = 'verified';
        clearError();
        pending.hidden = true;
        form.hidden = false;
        byId('deletion-account').textContent = data.account_label;
        byId('deletion-verification-link').removeAttribute('href');
        status.textContent = 'Ownership verified. Review the account and confirm your deletion request.';
        updateButtons();
      } else if (data.status === 'submitted' || data.status === 'completed') {
        showReceipt(data);
      } else if (data.status === 'failed') {
        reset();
        showError('Verification failed. Use a sign-in identity already linked to HSK AI and try again.');
      } else if (data.status === 'pending') {
        if (retryAction === checkStatus) clearError();
        timer = setTimeout(checkStatus, Math.min(1800, Math.max(1, request.expiresAt - Date.now())));
      } else {
        throw new Error('unexpected_status');
      }
    } catch (failure) {
      if (current !== generation) return;
      if (failure.status === 410) {
        reset();
        showError(failureMessage(failure));
      } else {
        showError(failureMessage(failure), checkStatus);
      }
    }
  }

  async function start(provider) {
    if (busy || request || !available.includes(provider)) return;
    // Open synchronously during the user's click so mobile popup protection can allow it.
    const popup = window.open('about:blank', '_blank');
    if (popup) popup.opener = null;
    clearError();
    busy = true;
    updateButtons();
    const current = ++generation;
    status.textContent = 'Starting ownership verification…';
    try {
      const data = await api('start', { provider });
      if (current !== generation) { if (popup) popup.close(); return; }
      if (!data.request_id || !data.secret || data.status !== 'pending' || !Number.isFinite(data.expires_in) || data.expires_in <= 0) throw new Error('invalid_challenge');
      const url = verificationUrl(provider, provider === 'telegram' ? data.bot_deep_link : data.authorize_url);
      request = { request_id: data.request_id, secret: data.secret, status: 'pending', expiresAt: Date.now() + Math.min(600, data.expires_in) * 1000 };
      pending.hidden = false;
      restart.hidden = false;
      byId('deletion-verification-link').href = url;
      byId('deletion-verification-link').textContent = provider === 'telegram' ? 'Open Telegram verification' : 'Open ' + (provider === 'google' ? 'Google' : 'Apple') + ' verification';
      byId('deletion-instructions').textContent = provider === 'telegram' ? 'Open the bot, explicitly verify ownership there, then return to this page. Your deletion request is submitted only after you confirm here.' : 'Finish sign-in in the new tab, then return to this page. Sign-in verifies ownership; you still need to confirm deletion here.';
      status.textContent = 'Waiting for ownership verification. Keep this page open.';
      if (popup) popup.location.replace(url);
      else showError('Your browser blocked the new tab. Use the Open verification link below, then return here.');
      busy = false;
      updateButtons();
      timer = setTimeout(checkStatus, 500);
    } catch (failure) {
      if (popup) popup.close();
      if (current !== generation) return;
      reset();
      showError(failureMessage(failure));
    } finally {
      if (current === generation) { busy = false; updateButtons(); }
    }
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy || !consent.checked || !request || request.status !== 'verified') return;
    const current = generation;
    busy = true;
    clearError();
    updateButtons();
    try {
      const data = await api('confirm', { ...requestBody(), confirmation: 'DELETE' });
      if (current !== generation) return;
      if (data.status !== 'submitted' && data.status !== 'completed') throw new Error('unconfirmed_request');
      showReceipt(data);
    } catch (failure) {
      if (current !== generation) return;
      if (failure.status === 410) reset();
      showError(failureMessage(failure));
    } finally {
      if (current === generation) { busy = false; updateButtons(); }
    }
  });
  consent.addEventListener('change', updateButtons);
  receiptCheck.addEventListener('click', checkReceiptStatus);
  buttons.forEach((button) => button.addEventListener('click', () => start(button.dataset.provider)));
  retry.addEventListener('click', () => { if (retryAction) retryAction(); });
  restart.addEventListener('click', reset);
  loadProviders();
}());
