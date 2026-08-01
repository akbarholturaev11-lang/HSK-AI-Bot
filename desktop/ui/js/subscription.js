const PLAN_ORDER = ["1_month", "3_months", "10_days"];
const METHOD_ORDER = ["visa", "alipay", "wechat"];
const SCREENSHOT_TYPES = new Set([
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/webp",
]);
const MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024;

function node(tag, className = "", text = "") {
  const value = document.createElement(tag);
  if (className) value.className = className;
  if (text !== "") value.textContent = String(text);
  return value;
}

function normalizedDate(value, language) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  const locale = language === "ru" ? "ru-RU" : language === "tj" ? "tg-TJ" : "uz-UZ";
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parsed);
}

function safeQrSource(value) {
  const source = String(value || "");
  return /^data:image\/(?:jpeg|jpg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(source)
    ? source
    : "";
}

function availableMethods(overview) {
  const prices = overview?.prices || {};
  return METHOD_ORDER.filter(
    (method) => Object.keys(prices[method] || {}).length > 0,
  );
}

function availablePlans(overview, method) {
  const prices = overview?.prices?.[method] || {};
  return PLAN_ORDER.filter((plan) => prices[plan]);
}

function fileDataUrl(file) {
  if (!file || !SCREENSHOT_TYPES.has(String(file.type || "").toLowerCase())) {
    return Promise.reject(new Error("desktop_payment_file_type_invalid"));
  }
  if (!Number.isFinite(file.size) || file.size <= 0 || file.size > MAX_SCREENSHOT_BYTES) {
    return Promise.reject(new Error("desktop_payment_file_too_large"));
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("desktop_payment_file_read_failed"));
    reader.readAsDataURL(file);
  });
}

export class DesktopSubscriptionController {
  constructor({
    host,
    bridge,
    t,
    language,
    onSessionExpired,
    onAccessChanged,
    onToast,
  }) {
    this.host = host;
    this.bridge = bridge;
    this.t = t;
    this.language = language;
    this.onSessionExpired = onSessionExpired;
    this.onAccessChanged = onAccessChanged;
    this.onToast = onToast;
    this.user = null;
    this.overview = null;
    this.plan = "1_month";
    this.method = "visa";
    this.country = "tj";
    this.quote = null;
    this.screenshotDataUrl = "";
    this.screenshotName = "";
    this.loading = false;
    this.quoting = false;
    this.submitting = false;
    this.errorCode = "";
  }

  setLanguage(language) {
    this.language = language;
    if (this.host?.isConnected) this.render();
  }

  setUser(user) {
    this.user = user || null;
  }

  resetCheckout() {
    this.quote = null;
    this.screenshotDataUrl = "";
    this.screenshotName = "";
    this.errorCode = "";
  }

  ensureSelection() {
    const methods = availableMethods(this.overview);
    if (!methods.includes(this.method)) this.method = methods[0] || "visa";
    const plans = availablePlans(this.overview, this.method);
    if (!plans.includes(this.plan)) this.plan = plans[0] || "1_month";
  }

  async open({ refresh = false } = {}) {
    if (!this.overview || refresh) await this.refresh();
    else this.render();
  }

  async refresh() {
    if (this.loading || this.submitting) return;
    this.loading = true;
    this.errorCode = "";
    this.render();
    try {
      const previousPaid = Boolean(this.overview?.access?.is_paid);
      const result = await this.bridge.subscriptionOverview();
      if (!result || result.ok !== true || !result.access) {
        throw new Error("desktop_subscription_payload_invalid");
      }
      this.overview = result;
      this.ensureSelection();
      if (Boolean(result.access.is_paid) !== previousPaid) {
        this.onAccessChanged?.(result.access);
      }
    } catch (error) {
      if (this.isSessionError(error)) return;
      this.errorCode = error?.code || error?.message || "desktop_subscription_unavailable";
    } finally {
      this.loading = false;
      this.render();
    }
  }

  isSessionError(error) {
    if (typeof this.onSessionExpired !== "function") return false;
    return this.onSessionExpired(error) === true;
  }

  choosePlan(plan) {
    if (!availablePlans(this.overview, this.method).includes(plan)) return;
    this.plan = plan;
    this.resetCheckout();
    this.render();
  }

  chooseMethod(method) {
    if (!availableMethods(this.overview).includes(method)) return;
    this.method = method;
    this.ensureSelection();
    this.resetCheckout();
    this.render();
  }

  async loadQuote() {
    if (this.quoting || this.submitting || this.overview?.access?.is_paid) return;
    this.quoting = true;
    this.errorCode = "";
    this.quote = null;
    this.render();
    try {
      const result = await this.bridge.subscriptionQuote(
        this.plan,
        this.method,
        this.method === "visa" ? this.country : null,
      );
      if (!result || result.ok !== true || !result.quote) {
        throw new Error("desktop_subscription_quote_invalid");
      }
      this.quote = result.quote;
    } catch (error) {
      if (this.isSessionError(error)) return;
      this.errorCode = error?.code || error?.message || "desktop_subscription_quote_failed";
    } finally {
      this.quoting = false;
      this.render();
    }
  }

  async selectScreenshot(file) {
    try {
      this.screenshotDataUrl = await fileDataUrl(file);
      this.screenshotName = String(file.name || this.t("paymentScreenshot"));
      this.errorCode = "";
    } catch (error) {
      this.screenshotDataUrl = "";
      this.screenshotName = "";
      this.errorCode = error?.message || "desktop_payment_file_invalid";
    }
    this.render();
  }

  async submit() {
    if (
      this.submitting ||
      !this.quote ||
      !this.screenshotDataUrl ||
      this.overview?.access?.is_paid
    ) {
      if (!this.screenshotDataUrl) this.onToast?.(this.t("paymentScreenshotRequired"));
      return;
    }
    this.submitting = true;
    this.errorCode = "";
    this.render();
    try {
      const result = await this.bridge.subscriptionSubmit(
        this.plan,
        this.method,
        this.method === "visa" ? this.country : null,
        this.screenshotDataUrl,
        this.overview?.attempt_id || null,
      );
      if (!result || result.ok !== true || result.status !== "pending") {
        throw new Error("desktop_subscription_submit_invalid");
      }
      this.quote = null;
      this.screenshotDataUrl = "";
      this.screenshotName = "";
      this.overview = null;
      this.submitting = false;
      await this.refresh();
      this.onToast?.(this.t("paymentSent"));
    } catch (error) {
      if (this.isSessionError(error)) return;
      this.errorCode = error?.code || error?.message || "desktop_subscription_submit_failed";
    } finally {
      this.submitting = false;
      this.render();
    }
  }

  render() {
    if (!this.host) return;
    this.host.replaceChildren();
    this.host.dataset.loading = String(this.loading || this.quoting || this.submitting);

    if (this.loading && !this.overview) {
      const loading = node("section", "subscription-state card-panel");
      loading.append(node("div", "spinner"), node("p", "", this.t("subscriptionLoading")));
      this.host.append(loading);
      return;
    }

    if (!this.overview) {
      this.host.append(this.renderErrorState());
      return;
    }

    const access = this.overview.access || {};
    if (access.state === "blocked") {
      const blocked = node("section", "subscription-state card-panel");
      blocked.append(
        node("p", "eyebrow", this.t("accountAccess")),
        node("h3", "", this.t("subscriptionBlockedTitle")),
        node("p", "muted", this.t("subscriptionBlockedBody")),
      );
      this.host.append(blocked);
      return;
    }

    if (access.is_paid) {
      this.host.append(this.renderPaid(access));
      return;
    }

    if (this.overview.pending_payment) {
      this.host.append(this.renderPending(this.overview.pending_payment));
      return;
    }

    this.ensureSelection();
    this.host.append(this.renderCheckout());
  }

  renderErrorState() {
    const wrap = node("section", "subscription-state card-panel");
    wrap.append(
      node("div", "subscription-state-mark", "!"),
      node("h3", "", this.t("subscriptionUnavailableTitle")),
      node("p", "muted", this.t("subscriptionUnavailableBody")),
    );
    const retry = node("button", "primary-button", this.t("retry"));
    retry.type = "button";
    retry.addEventListener("click", () => this.refresh());
    wrap.append(retry);
    return wrap;
  }

  renderPaid(access) {
    const card = node("section", "subscription-active card-panel");
    const seal = node("div", "subscription-seal", "✓");
    const copy = node("div", "subscription-active-copy");
    copy.append(
      node("p", "eyebrow", this.t("premiumAccess")),
      node("h3", "", this.t("subscriptionActiveTitle")),
      node(
        "p",
        "muted",
        access.expires_at
          ? this.t("subscriptionActiveUntil", {
              date: normalizedDate(access.expires_at, this.language),
            })
          : this.t("paidAccessDescription"),
      ),
      node("small", "subscription-renew-note", this.t("subscriptionRenewLocked")),
    );
    const refresh = node("button", "secondary-button", this.t("subscriptionRefresh"));
    refresh.type = "button";
    refresh.addEventListener("click", () => this.refresh());
    card.append(seal, copy, refresh);
    return card;
  }

  renderPending(payment) {
    const card = node("section", "subscription-pending card-panel");
    card.append(
      node("div", "subscription-state-mark", "…"),
      node("p", "eyebrow", this.t("paymentReview")),
      node("h3", "", this.t("paymentPendingTitle")),
      node("p", "muted", this.t("paymentPendingBody")),
      node(
        "strong",
        "pending-payment-meta",
        `${this.t(`plan_${payment.plan_type}`)} · ${payment.amount || "—"} ${payment.currency || ""}`,
      ),
    );
    const refresh = node("button", "primary-button", this.t("subscriptionRefresh"));
    refresh.type = "button";
    refresh.addEventListener("click", () => this.refresh());
    card.append(refresh);
    return card;
  }

  renderCheckout() {
    const shell = node("div", "subscription-layout");
    const chooser = node("section", "subscription-chooser card-panel");
    chooser.append(
      node("p", "eyebrow", this.t("subscriptionChoosePlan")),
      node("h3", "", this.t("subscriptionUnlockTitle")),
      node("p", "muted", this.t("subscriptionUnlockBody")),
    );

    const plans = node("div", "subscription-plans");
    availablePlans(this.overview, this.method).forEach((plan) => {
      const info = this.overview.prices?.[this.method]?.[plan] || {};
      const button = node("button", "subscription-plan");
      button.type = "button";
      button.dataset.testid = "subscription-plan";
      button.dataset.plan = plan;
      button.classList.toggle("is-active", plan === this.plan);
      button.append(
        node("span", "subscription-plan-name", this.t(`plan_${plan}`)),
        node("strong", "", `${info.final_amount ?? "—"} ${info.currency || ""}`),
      );
      if (info.discount_applied) {
        button.append(
          node("small", "subscription-discount", `−${Number(info.discount_percent || 0)}%`),
        );
      }
      button.addEventListener("click", () => this.choosePlan(plan));
      plans.append(button);
    });
    chooser.append(plans);

    chooser.append(node("h4", "subscription-subtitle", this.t("paymentMethod")));
    const methods = node("div", "payment-methods");
    availableMethods(this.overview).forEach((method) => {
      const button = node("button", "payment-method");
      button.type = "button";
      button.dataset.testid = "payment-method";
      button.dataset.method = method;
      button.classList.toggle("is-active", method === this.method);
      button.textContent = this.t(`method_${method}`);
      button.addEventListener("click", () => this.chooseMethod(method));
      methods.append(button);
    });
    chooser.append(methods);

    if (this.method === "visa") chooser.append(this.renderCountries());

    const quoteButton = node(
      "button",
      "primary-button subscription-quote-button",
      this.quoting ? this.t("subscriptionQuoteLoading") : this.t("subscriptionContinue"),
    );
    quoteButton.type = "button";
    quoteButton.disabled = this.quoting || this.submitting;
    quoteButton.addEventListener("click", () => this.loadQuote());
    chooser.append(quoteButton);

    const payment = this.quote ? this.renderPayment() : this.renderCheckoutIntro();
    shell.append(chooser, payment);
    return shell;
  }

  renderCountries() {
    const wrap = node("div", "payment-countries");
    wrap.append(node("span", "subscription-field-label", this.t("cardCountry")));
    const choices = node("div", "payment-country-list");
    ["tj", "uz", "ru", "other"].forEach((country) => {
      const button = node("button", "payment-country", this.t(`country_${country}`));
      button.type = "button";
      button.classList.toggle("is-active", this.country === country);
      button.addEventListener("click", () => {
        this.country = country;
        this.resetCheckout();
        this.render();
      });
      choices.append(button);
    });
    wrap.append(choices);
    return wrap;
  }

  renderCheckoutIntro() {
    const card = node("section", "subscription-preview card-panel");
    card.append(
      node("div", "subscription-preview-glyph", "会"),
      node("p", "eyebrow", this.t("singleAccount")),
      node("h3", "", this.t("subscriptionPreviewTitle")),
      node("p", "muted", this.t("subscriptionPreviewBody")),
    );
    const benefits = node("ul", "subscription-benefits");
    ["subscriptionBenefitCourse", "subscriptionBenefitProgress", "subscriptionBenefitDesktop"].forEach(
      (key) => benefits.append(node("li", "", this.t(key))),
    );
    card.append(benefits);
    if (this.errorCode) card.append(node("p", "form-error", this.t(this.errorCode)));
    return card;
  }

  renderPayment() {
    const quote = this.quote || {};
    const card = node("section", "subscription-payment card-panel");
    card.append(
      node("p", "eyebrow", this.t("paymentInstructions")),
      node("h3", "", this.t("paymentAmountTitle")),
    );
    const amount = node("div", "payment-amount");
    amount.append(
      node("strong", "", quote.pay_amount || quote.final_amount || "—"),
      node("span", "", quote.pay_currency || quote.final_currency || ""),
    );
    card.append(amount);
    if (quote.discount_applied) {
      card.append(
        node(
          "p",
          "payment-discount-note",
          this.t("paymentDiscountApplied", { percent: Number(quote.discount_percent || 0) }),
        ),
      );
    }

    const details = node("div", "payment-details");
    if (this.method === "visa") {
      details.append(
        node("span", "subscription-field-label", this.t("paymentDetails")),
        node("pre", "payment-details-text", quote.payment_details || this.t("paymentDetailsMissing")),
      );
    } else {
      const source = safeQrSource(quote.qr?.image_data_url);
      details.append(node("span", "subscription-field-label", this.t("paymentQr")));
      if (source) {
        const image = node("img", "payment-qr");
        image.src = source;
        image.alt = this.t("paymentQr");
        details.append(image);
      } else {
        details.append(node("p", "muted", this.t("paymentQrMissing")));
      }
    }
    card.append(details);

    const upload = node("label", "payment-upload");
    upload.setAttribute("for", "payment-screenshot");
    upload.append(
      node("span", "payment-upload-mark", this.screenshotDataUrl ? "✓" : "+"),
      node("strong", "", this.screenshotName || this.t("paymentScreenshot")),
      node("small", "", this.t("paymentScreenshotHint")),
    );
    const input = node("input", "sr-only");
    input.id = "payment-screenshot";
    input.type = "file";
    input.accept = "image/jpeg,image/png,image/webp";
    input.addEventListener("change", () => this.selectScreenshot(input.files?.[0]));
    upload.append(input);
    card.append(upload);

    if (this.errorCode) card.append(node("p", "form-error", this.t(this.errorCode)));
    const submit = node(
      "button",
      "primary-button payment-submit",
      this.submitting ? this.t("paymentSending") : this.t("paymentSubmit"),
    );
    submit.id = "payment-submit";
    submit.type = "button";
    submit.disabled = this.submitting || !this.screenshotDataUrl;
    submit.addEventListener("click", () => this.submit());
    const status = node("p", "payment-status muted");
    status.id = "payment-status";
    status.setAttribute("role", "status");
    card.append(submit, status);
    return card;
  }
}
