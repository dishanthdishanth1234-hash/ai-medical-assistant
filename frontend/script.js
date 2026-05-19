/**
 * AI Medical Assistant — frontend
 * Auth (OTP registration), dashboard, diet plan, appointments API, doctors, structured symptoms.
 */
(function () {
  const TOKEN_KEY = "medassist_token";
  const THEME_KEY = "medassist_theme";
  const API_BASE = window.location.origin;
  let currentUserCache = null;
  let publicConfigCache = null;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function setPageLoading(on) {
    const el = $("#pageLoader");
    if (!el) return;
    el.hidden = !on;
    el.setAttribute("aria-busy", on ? "true" : "false");
    el.setAttribute("aria-hidden", on ? "false" : "true");
    document.body.style.overflow = on ? "hidden" : "";
  }

  function showAlertBanner(message, type = "error") {
    const b = $("#alertBanner");
    if (!b) return;
    b.textContent = message;
    b.className = "alert-banner " + (type === "success" ? "success" : "error");
    b.hidden = false;
    clearTimeout(showAlertBanner._t);
    showAlertBanner._t = setTimeout(() => {
      b.hidden = true;
    }, 5000);
  }

  function toast(msg, type = "info") {
    const el = $("#toast");
    if (!el) return;
    el.textContent = msg;
    el.className = "toast " + (type === "success" ? "success" : type === "error" ? "error" : "");
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      el.hidden = true;
    }, 3500);
  }

  function formatApiDetail(detail) {
    if (detail == null) return "Request failed";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => {
          if (typeof d === "string") return d;
          if (d && typeof d === "object") {
            const loc = (d.loc || []).filter((x) => x !== "body").join(".");
            return `${loc ? loc + ": " : ""}${d.msg || d.type || JSON.stringify(d)}`;
          }
          return String(d);
        })
        .join("; ");
    }
    if (typeof detail === "object" && detail.msg) return detail.msg;
    return JSON.stringify(detail);
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "dark") document.documentElement.dataset.theme = "dark";
    $$("#themeToggle").forEach((btn) =>
      btn.addEventListener("click", () => {
        const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        if (next === "dark") {
          document.documentElement.dataset.theme = "dark";
          localStorage.setItem(THEME_KEY, "dark");
        } else {
          delete document.documentElement.dataset.theme;
          localStorage.setItem(THEME_KEY, "light");
        }
      })
    );
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(t) {
    if (!t) {
      localStorage.removeItem(TOKEN_KEY);
      currentUserCache = null;
    } else {
      localStorage.setItem(TOKEN_KEY, t);
    }
  }

  async function api(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (
      !headers["Content-Type"] &&
      options.body &&
      typeof options.body === "object" &&
      !(options.body instanceof FormData)
    ) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(options.body);
    }
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    const text = await res.text();
    let data = null;
    if (res.status === 204) {
      data = null;
    } else if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text || "Invalid server response" };
      }
    }
    if (!res.ok) {
      const msg = formatApiDetail(data?.detail) || data?.message || `Request failed (${res.status})`;
      const err = new Error(msg);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function setButtonLoading(button, isLoading, loadingText) {
    if (!button) return;
    const textEl =
      $(".btn-text", button) || $(".analyze-label", button) || (button.id === "healthSubmit" ? button : null) || button;
    if (!button.dataset.defaultText) {
      button.dataset.defaultText = textEl.textContent;
    }
    button.disabled = isLoading;
    button.setAttribute("aria-busy", isLoading ? "true" : "false");
    textEl.textContent = isLoading && loadingText ? loadingText : button.dataset.defaultText;
  }

  async function fetchCurrentUser(force = false) {
    if (!getToken()) return null;
    if (!force && currentUserCache) return currentUserCache;
    currentUserCache = await api("/me");
    return currentUserCache;
  }

  function ensureAdminLinks() {
    const navs = $$(".header-nav, .footer-nav");
    navs.forEach((nav) => {
      if (!nav || nav.querySelector('[data-admin-link="1"]') || Array.from(nav.querySelectorAll("a")).some((a) => /admin\.html$/i.test(a.getAttribute("href") || ""))) return;
      const link = document.createElement("a");
      link.href = "admin.html";
      link.textContent = "Admin";
      link.setAttribute("data-admin-link", "1");
      link.className = nav.classList.contains("header-nav") ? "nav-link" : "";
      nav.appendChild(link);
    });
  }

  function applyPublicConfig(config) {
    if (!config) return;
    publicConfigCache = config;
    const disclaimer = $("#disclaimer");
    if (disclaimer) {
      disclaimer.innerHTML = `<strong>Medical disclaimer:</strong> ${escapeHtml(config.footer_text || "")}`;
    }
    const retention = $("#dataRetentionNotice");
    if (retention && config.data_retention_notice) {
      retention.textContent = config.data_retention_notice;
      retention.hidden = false;
    }
    const emailHint = $("#emailNotReadyHint");
    if (emailHint) emailHint.hidden = Boolean(config.email_ready);
    const em = $("#emergencyNumberDisplay");
    if (em) em.textContent = config.emergency_number || "112";
  }

  async function loadPublicConfig(force = false) {
    if (!force && publicConfigCache) return publicConfigCache;
    try {
      const cfg = await api("/public/app-config");
      applyPublicConfig(cfg);
      return cfg;
    } catch {
      return publicConfigCache;
    }
  }

  async function fetchFileBlob(path) {
    const headers = {};
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}${path}`, { headers });
    if (!res.ok) {
      const text = await res.text();
      let msg = `Request failed (${res.status})`;
      try {
        const data = JSON.parse(text);
        msg = formatApiDetail(data?.detail) || msg;
      } catch {
        if (text) msg = text;
      }
      throw new Error(msg);
    }
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "";
    const match = cd.match(/filename="([^"\\]+)"/);
    return { blob, filename: match ? match[1] : "download.pdf" };
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatAiText(raw) {
    const esc = escapeHtml(raw);
    return esc.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replaceAll("\n", "<br />");
  }

  function tryFormatStructuredJson(text) {
    try {
      const o = JSON.parse(text);
      if (o && typeof o.condition === "string" && typeof o.doctor_type === "string") {
        const pre = Array.isArray(o.precautions) ? o.precautions : [];
        return `<div class="symptom-structured">
          <div class="symptom-card"><h4>Condition (not a diagnosis)</h4><p>${escapeHtml(o.condition)}</p></div>
          <div class="symptom-card"><h4>Doctor type</h4><p>${escapeHtml(o.doctor_type)}</p></div>
          <div class="symptom-card"><h4>Precautions</h4><ul>${pre.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul></div>
          ${o.disclaimer ? `<div class="symptom-card"><h4>Disclaimer</h4><p>${escapeHtml(o.disclaimer)}</p></div>` : ""}
        </div>`;
      }
    } catch {
      /* not JSON */
    }
    return formatAiText(text);
  }

  function primePasswordToggle(btn, input) {
    const wrap = btn?.closest(".password-field");
    const glyph = $(".password-toggle-glyph", btn);
    if (!wrap || !input || !btn) return;
    wrap.style.position = "relative";
    wrap.style.display = "block";
    input.style.paddingRight = "56px";
    btn.style.position = "absolute";
    btn.style.top = "50%";
    btn.style.right = "10px";
    btn.style.transform = "translateY(-50%)";
    btn.style.width = "34px";
    btn.style.height = "34px";
    btn.style.marginRight = "0";
    btn.style.padding = "0";
    btn.style.border = "none";
    btn.style.background = "transparent";
    btn.style.color = "#4dabf7";
    btn.style.display = "grid";
    btn.style.placeItems = "center";
    btn.style.cursor = "pointer";
    btn.style.zIndex = "2";
    btn.style.appearance = "none";
    btn.style.webkitAppearance = "none";
    if (glyph) {
      glyph.style.display = "block";
      glyph.style.fontSize = "18px";
      glyph.style.lineHeight = "1";
    }
  }

  function syncPasswordToggle(btn, input) {
    const wrap = btn?.closest(".password-field");
    const visible = !!input && input.type === "text";
    const glyph = $(".password-toggle-glyph", btn);
    btn?.setAttribute("aria-pressed", String(visible));
    btn?.setAttribute("aria-label", visible ? "Hide password" : "Show password");
    btn?.setAttribute("title", visible ? "Hide password" : "Show password");
    btn?.classList.toggle("is-visible", visible);
    wrap?.classList.toggle("is-visible", visible);
    if (glyph) glyph.textContent = "\u{1F441}";
  }

  function initPasswordToggles(root = document) {
    $$("[data-password-toggle]", root).forEach((btn) => {
      const wrap = btn.closest(".password-field");
      const input = $("input", wrap);
      if (!input) return;
      primePasswordToggle(btn, input);
      syncPasswordToggle(btn, input);
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("mousedown", (e) => e.preventDefault());
      btn.addEventListener("click", () => {
        const caretStart = input.selectionStart;
        const caretEnd = input.selectionEnd;
        input.type = input.type === "password" ? "text" : "password";
        syncPasswordToggle(btn, input);
        btn.style.transform = "translateY(-50%)";
        input.focus({ preventScroll: true });
        if (typeof caretStart === "number" && typeof caretEnd === "number") {
          input.setSelectionRange(caretStart, caretEnd);
        }
      });
    });
  }

  function authPage() {
    $$(".otp-reveal").forEach((el) => el.remove());
    const tabs = $$(".tab");
    const panels = { login: $("#panel-login"), register: $("#panel-register") };
    initPasswordToggles();
    const forgotCard = $("#forgotPasswordCard");
    const resetEmail = $("#resetEmail");
    const resetOtpHint = $("#resetOtpHint");
    const verifyResetOtpForm = $("#verifyResetOtpForm");
    const resetPasswordForm = $("#resetPasswordForm");
    let resetOtpVerified = false;

    function resetForgotPasswordFlow(keepEmail = true) {
      const emailKeep = keepEmail ? (resetEmail?.value || "").trim() : "";
      verifyResetOtpForm?.reset();
      resetPasswordForm?.reset();
      if (resetEmail) resetEmail.value = emailKeep;
      if (resetOtpHint) {
        resetOtpHint.hidden = true;
        resetOtpHint.textContent = "";
      }
      if (verifyResetOtpForm) verifyResetOtpForm.hidden = true;
      if (resetPasswordForm) resetPasswordForm.hidden = true;
      if ($("#resendResetOtpBtn")) $("#resendResetOtpBtn").hidden = true;
      if ($("#verifyResetError")) {
        $("#verifyResetError").hidden = true;
        $("#verifyResetError").textContent = "";
      }
      if ($("#resetPasswordError")) {
        $("#resetPasswordError").hidden = true;
        $("#resetPasswordError").textContent = "";
      }
      resetOtpVerified = false;
      initPasswordToggles(forgotCard || document);
    }

    function openForgotPasswordCard() {
      tabs[0]?.click();
      if (forgotCard) forgotCard.hidden = false;
      resetForgotPasswordFlow();
      forgotCard?.scrollIntoView({ behavior: "smooth", block: "start" });
      resetEmail?.focus();
    }

    function closeForgotPasswordCard() {
      if (forgotCard) forgotCard.hidden = true;
      resetForgotPasswordFlow(false);
    }

    function resetRegisterWizard() {
      const emailKeep = ($("#regEmail")?.value || "").trim();
      $("#registerForm")?.reset();
      if ($("#regEmail")) $("#regEmail").value = emailKeep;
      const fs = $("#regFieldset");
      if (fs) fs.disabled = true;
      $("#registerStep2").hidden = true;
      $("#resendOtpBtn").hidden = true;
      const hint = $("#otpHint");
      if (hint) {
        hint.hidden = true;
        hint.textContent = "";
      }
      $("#registerError").hidden = true;
    }

    function unlockRegisterStep2(message) {
      const hint = $("#otpHint");
      if (hint) {
        hint.hidden = false;
        hint.textContent = message;
      }
      $("#registerStep2").hidden = false;
      const fs = $("#regFieldset");
      if (fs) fs.disabled = false;
      $("#resendOtpBtn").hidden = false;
      $("#regOtpInput")?.focus();
    }

    async function sendRegistrationOtp(triggerButton) {
      const emailEl = $("#regEmail");
      const email = (emailEl?.value || "").trim();
      if (!email) {
        showAlertBanner("Enter your email first.", "error");
        return;
      }
      const primaryButton = $("#sendOtpBtn");
      const activeButton = triggerButton || primaryButton;
      setButtonLoading(primaryButton, true, "Sending...");
      if (activeButton !== primaryButton) setButtonLoading(activeButton, true);
      try {
        const data = await api("/register/send-otp", { method: "POST", body: { email } });
        if (data.email_sent) {
          unlockRegisterStep2(
            data.message ||
              `Code sent to ${email}. Open your inbox — subject line starts with "Your Code -".`
          );
          toast("Code sending — check your inbox in a few seconds.", "success");
          return;
        }
        showAlertBanner(data.message || "Could not send verification email.", "error");
      } catch (ex) {
        showAlertBanner(
          ex.message ||
            "Could not send email. Ask the site owner to configure Gmail SMTP on Render, then try again.",
          "error"
        );
      } finally {
        setButtonLoading(primaryButton, false);
        if (activeButton !== primaryButton) setButtonLoading(activeButton, false);
      }
    }

    function unlockForgotPasswordOtpStep(message) {
      resetOtpHint.hidden = false;
      resetOtpHint.textContent = message;
      verifyResetOtpForm.hidden = false;
      $("#resendResetOtpBtn").hidden = false;
      $("#verifyResetError").hidden = true;
      $("#verifyResetError").textContent = "";
      $("#resetPasswordError").hidden = true;
      $("#resetPasswordError").textContent = "";
      resetPasswordForm.hidden = true;
      resetOtpVerified = false;
      verifyResetOtpForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
      $("#resetOtpInput")?.focus();
    }

    async function sendResetOtp(triggerButton) {
      const email = (resetEmail?.value || "").trim();
      if (!email) {
        showAlertBanner("Enter your registered email first.", "error");
        return;
      }
      const primaryButton = $("#sendResetOtpBtn");
      const activeButton = triggerButton || primaryButton;
      setButtonLoading(primaryButton, true, "Sending...");
      if (activeButton !== primaryButton) setButtonLoading(activeButton, true);
      try {
        const data = await api("/forgot-password/send-otp", { method: "POST", body: { email } });
        if (data.email_sent) {
          unlockForgotPasswordOtpStep(
            data.message ||
              `Reset code sent to ${email}. Check your inbox — subject: "Your Code - …".`
          );
          toast("Check your email for the reset code.", "success");
          return;
        }
        showAlertBanner(data.message || "Could not send reset email.", "error");
      } catch (ex) {
        showAlertBanner(
          ex.message ||
            "Could not send email. Configure Gmail SMTP on the server, then try again.",
          "error"
        );
      } finally {
        setButtonLoading(primaryButton, false);
        if (activeButton !== primaryButton) setButtonLoading(activeButton, false);
      }
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const name = tab.dataset.tab;
        if (name === "register") resetRegisterWizard();
        tabs.forEach((t) => {
          t.classList.toggle("active", t === tab);
          t.setAttribute("aria-selected", String(t === tab));
        });
        Object.entries(panels).forEach(([k, p]) => {
          if (!p) return;
          const on = k === name;
          p.classList.toggle("active", on);
          p.toggleAttribute("hidden", !on);
        });
      });
    });

    $("#loginForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = e.target;
      const err = $("#loginError");
      const submitButton = form.querySelector('button[type="submit"]');
      err.hidden = true;
      const fd = new FormData(form);
      setButtonLoading(submitButton, true, "Signing in...");
      try {
        const data = await api("/login", {
          method: "POST",
          body: { email: fd.get("email"), password: fd.get("password") },
        });
        setToken(data.access_token);
        const me = await fetchCurrentUser(true);
        toast("Signed in successfully", "success");
        window.location.href = me?.role === "admin" ? "admin.html" : "dashboard.html";
      } catch (ex) {
        err.textContent = ex.message || "Login failed";
        err.hidden = false;
        showAlertBanner(ex.message || "Login failed", "error");
      } finally {
        setButtonLoading(submitButton, false);
      }
    });

    $("#sendOtpBtn")?.addEventListener("click", (e) => sendRegistrationOtp(e.currentTarget));
    $("#resendOtpBtn")?.addEventListener("click", (e) => sendRegistrationOtp(e.currentTarget));
    $("#openForgotPassword")?.addEventListener("click", () => openForgotPasswordCard());
    $("#closeForgotPassword")?.addEventListener("click", () => closeForgotPasswordCard());
    $("#sendResetOtpBtn")?.addEventListener("click", (e) => sendResetOtp(e.currentTarget));
    $("#resendResetOtpBtn")?.addEventListener("click", (e) => sendResetOtp(e.currentTarget));

    $("#verifyResetOtpForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = $("#verifyResetError");
      const submitButton = e.target.querySelector('button[type="submit"]');
      err.hidden = true;
      setButtonLoading(submitButton, true, "Verifying...");
      try {
        await api("/forgot-password/verify-otp", {
          method: "POST",
          body: {
            email: ($("#resetEmail")?.value || "").trim(),
            otp: ($("#resetOtpInput")?.value || "").trim(),
          },
        });
        resetOtpVerified = true;
        resetPasswordForm.hidden = false;
        initPasswordToggles(resetPasswordForm);
        $("#resetNewPassword")?.focus();
        resetPasswordForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
        toast("OTP verified. Set your new password.", "success");
      } catch (ex) {
        err.textContent = ex.message || "OTP verification failed";
        err.hidden = false;
      } finally {
        setButtonLoading(submitButton, false);
      }
    });

    $("#registerForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = e.target;
      const err = $("#registerError");
      const submitButton = form.querySelector('button[type="submit"]');
      err.hidden = true;
      if ($("#regFieldset")?.disabled) {
        err.textContent = "Complete step 1: enter your email and click “Send verification code”.";
        err.hidden = false;
        return;
      }
      const fd = new FormData(form);
      const email = ($("#regEmail")?.value || "").trim();
      if (!email) {
        err.textContent = "Email is required (use the field in step 1).";
        err.hidden = false;
        return;
      }
      const payload = {
        name: fd.get("name"),
        email,
        password: fd.get("password"),
        otp: (fd.get("otp") || "").trim(),
      };
      const age = fd.get("age");
      const w = fd.get("weight_kg");
      const h = fd.get("height_cm");
      const mh = fd.get("medical_history");
      if (age) payload.age = Number(age);
      if (w) payload.weight_kg = Number(w);
      if (h) payload.height_cm = Number(h);
      if (mh) payload.medical_history = String(mh);
      setButtonLoading(submitButton, true, "Creating...");
      try {
        await api("/register", { method: "POST", body: payload });
        toast("Account created — please sign in.", "success");
        resetRegisterWizard();
        tabs[0].click();
      } catch (ex) {
        err.textContent = ex.message || "Registration failed";
        err.hidden = false;
        showAlertBanner(ex.message || "Registration failed", "error");
      } finally {
        setButtonLoading(submitButton, false);
      }
    });

    $("#resetPasswordForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = $("#resetPasswordError");
      const submitButton = e.target.querySelector('button[type="submit"]');
      err.hidden = true;
      if (!resetOtpVerified) {
        err.textContent = "Verify your OTP before setting a new password.";
        err.hidden = false;
        return;
      }
      setButtonLoading(submitButton, true, "Resetting...");
      try {
        await api("/forgot-password/reset", {
          method: "POST",
          body: {
            email: ($("#resetEmail")?.value || "").trim(),
            otp: ($("#resetOtpInput")?.value || "").trim(),
            new_password: $("#resetNewPassword")?.value || "",
          },
        });
        toast("Password reset successful - please sign in.", "success");
        closeForgotPasswordCard();
        $("#loginForm")?.reset();
        initPasswordToggles($("#loginForm") || document);
        tabs[0]?.click();
      } catch (ex) {
        err.textContent = ex.message || "Password reset failed";
        err.hidden = false;
      } finally {
        setButtonLoading(submitButton, false);
      }
    });
  }

  function requireAuth() {
    if (!getToken()) {
      window.location.href = "index.html";
      return false;
    }
    return true;
  }

  function appendBubble(container, role, htmlOrText, isHtml) {
    const div = document.createElement("div");
    div.className = `bubble ${role}`;
    if (isHtml) div.innerHTML = htmlOrText;
    else div.textContent = htmlOrText;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  const SAMPLE_HOSPITALS = [
    {
      name: "Kasturba Medical Hospital (KMC)",
      address: "KMC Hospital, Attavar, Mangaluru, Karnataka 575001",
      phone: "0824 228 5000",
    },
    {
      name: "Life Care Diagnostic and Health Center",
      address: "Noor Vista, Nawayath Colony, Jali Road, Bhatkal, Uttara Kannada, Karnataka 581320",
      phone: "083859 92233",
    },
    {
      name: "St Ignatius Hospital",
      address: "Prabhat Nagar, Honavar, Karnataka 581334",
      phone: "083872 20345",
    },
  ];

  const HEALTH_TIPS = [
    "Keep a consistent sleep schedule — recovery and immunity benefit from regular rest.",
    "Aim for gradual activity increases; even short walks help cardiovascular health.",
    "Hydration supports energy and cognition; adjust fluid intake if your clinician advised limits.",
    "Wash hands before eating and after being in crowded spaces to reduce common infections.",
    "Schedule routine checkups; early detection is easier to manage than late-stage issues.",
  ];

  function dashboardPage() {
    if (!requireAuth()) return;

    $("#logoutBtn")?.addEventListener("click", () => {
      setToken(null);
      window.location.href = "index.html";
    });

    const chatWindow = $("#chatWindow");
    const chatForm = $("#chatForm");
    const chatInput = $("#chatInput");
    const analyzeBtn = $("#analyzeSend");
    const aiStatus = $("#aiStatus");
    let doctorDirectory = [];
    let activeDoctor = null;

    function formatDoctorDisplayName(name) {
      const raw = String(name || "").trim();
      const stripped = raw.replace(/^dr\.?\s+/i, "").trim();
      return `Dr. ${stripped || "Doctor"}`;
    }

    function setAnalysisLoading(isLoading) {
      if (analyzeBtn) {
        analyzeBtn.disabled = isLoading;
        const label = $(".analyze-label", analyzeBtn);
        if (label) {
          if (!analyzeBtn.dataset.defaultLabel) analyzeBtn.dataset.defaultLabel = label.textContent;
          label.textContent = isLoading ? "Analyzing…" : analyzeBtn.dataset.defaultLabel;
        }
      }
      if (aiStatus) aiStatus.textContent = isLoading ? "Analyzing…" : "Ready";
    }

    async function refreshProfile() {
      const me = await api("/me");
      currentUserCache = me;
      if (me.role === "admin") ensureAdminLinks();
      $("#welcomeLine").textContent = `Signed in as ${me.name}`;
      const stats = $("#profileStats");
      stats.innerHTML = "";
      const rows = [
        ["Email", me.email],
        ["Age", me.age ?? "—"],
        ["Weight", me.weight_kg != null ? `${me.weight_kg} kg` : "—"],
        ["Height", me.height_cm != null ? `${me.height_cm} cm` : "—"],
        ["Medical history", me.medical_history ? "On file" : "—"],
      ];
      rows.forEach(([k, v]) => {
        const row = document.createElement("div");
        row.className = "stat-row";
        row.innerHTML = `<span class="k">${escapeHtml(k)}</span><span class="v">${escapeHtml(String(v))}</span>`;
        stats.appendChild(row);
      });

      $("#bmiWeight").value = me.weight_kg ?? "";
      $("#bmiHeight").value = me.height_cm ?? "";
      $("#healthWeight").value = me.weight_kg ?? "";
      $("#healthHeight").value = me.height_cm ?? "";

      const pf = $("#profileForm");
      if (pf) {
        pf.name.value = me.name || "";
        pf.age.value = me.age ?? "";
        pf.weight_kg.value = me.weight_kg ?? "";
        pf.height_cm.value = me.height_cm ?? "";
        pf.medical_history.value = me.medical_history || "";
      }
      return me;
    }

    async function refreshHistory() {
      const items = await api("/chat/history?limit=40");
      const box = $("#historyScroll");
      box.innerHTML = "";
      items
        .slice()
        .reverse()
        .forEach((it) => {
          const div = document.createElement("div");
          div.className = "history-item";
          const assistantHtml = tryFormatStructuredJson(it.response);
          const rawMessage = String(it.message || "");
          const cleanedMessage = rawMessage
            .replace(/^\[DoctorChat:\d+\]\s*/, "")
            .replace("__intro__", "Doctor introduction")
            .trim();
          const label = /^\[DoctorChat:\d+\]/.test(rawMessage) ? "Doctor chat" : "You";
          div.innerHTML = `<small>${escapeHtml(new Date(it.created_at).toLocaleString())}</small>
            <div><strong>${escapeHtml(label)}:</strong> ${escapeHtml(cleanedMessage)}</div>
            <div><strong>Assistant:</strong> ${assistantHtml}</div>`;
          box.appendChild(div);
        });
    }

    async function refreshHealthTable() {
      const rows = await api("/health-data?limit=60");
      const tbody = $("#healthTable tbody");
      tbody.innerHTML = "";
      rows.forEach((r) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${escapeHtml(r.recorded_date)}</td><td>${escapeHtml(String(r.weight_kg))} kg</td><td>${escapeHtml(
          String(r.bmi)
        )}</td>`;
        tbody.appendChild(tr);
      });
    }

    async function loadDoctors() {
      const grid = $("#doctorGrid");
      if (!grid) return;
      grid.innerHTML = `<p class="muted">Loading doctors…</p>`;
      try {
        const doctors = await api("/doctors/");
        doctorDirectory = doctors;
        grid.innerHTML = "";
        doctors.forEach((d) => {
          const card = document.createElement("article");
          card.className = "doctor-card";
          card.setAttribute("data-doctor-id", String(d.id));
          card.tabIndex = 0;
          card.setAttribute("role", "button");
          card.setAttribute("aria-label", `Open details for ${formatDoctorDisplayName(d.name)}, ${d.specialization}`);
          card.innerHTML = `
            <img class="doctor-photo" src="${escapeHtml(d.photo_url)}" alt="" loading="lazy" width="400" height="300" />
            <div class="doctor-card-body">
              <h3>${escapeHtml(d.name)}</h3>
              <div class="doctor-meta">${escapeHtml(d.specialization)} · ${escapeHtml(String(d.experience_years))} yrs exp.</div>
              <button type="button" class="btn primary small book-doc-btn">Book appointment</button>
            </div>`;
          card.addEventListener("click", () => openDoctorDetailModal(d));
          card.addEventListener("keydown", (e) => {
            if (e.key !== "Enter" && e.key !== " ") return;
            e.preventDefault();
            openDoctorDetailModal(d);
          });
          card.querySelector(".book-doc-btn")?.addEventListener("click", (e) => {
            e.stopPropagation();
            openBookModal(d.id, d.name);
          });
          grid.appendChild(card);
        });
      } catch (e) {
        doctorDirectory = [];
        grid.innerHTML = `<p class="muted">Could not load doctors.</p>`;
      }
    }

    function highlightRecommendedDoctors(doctors) {
      const selectedIds = new Set((doctors || []).map((doc) => String(doc.id)));
      $$(".doctor-card").forEach((card) => {
        const isMatch = selectedIds.has(card.getAttribute("data-doctor-id") || "");
        card.classList.toggle("is-recommended", isMatch);
        const existingBadge = $(".doctor-badge", card);
        if (isMatch && !existingBadge) {
          const badge = document.createElement("div");
          badge.className = "doctor-badge";
          badge.textContent = "Recommended for this symptom";
          $(".doctor-card-body", card)?.prepend(badge);
        }
        if (!isMatch && existingBadge) existingBadge.remove();
      });
    }

    const bookModal = $("#bookModal");
    const doctorDetailModal = $("#doctorDetailModal");
    const doctorChatModal = $("#doctorChatModal");

    function openDoctorDetailModal(doctor) {
      activeDoctor = doctor;
      $("#doctorDetailPhoto").src = doctor.photo_url;
      $("#doctorDetailName").textContent = formatDoctorDisplayName(doctor.name);
      $("#doctorDetailSpec").textContent = `${doctor.specialization} · ${doctor.experience_years} years experience`;
      doctorDetailModal.hidden = false;
    }

    function openBookModal(doctorId, doctorName) {
      $("#bookDoctorId").value = String(doctorId);
      $("#bookDoctorLabel").textContent = doctorName || "Selected doctor";
      const t = new Date().toISOString().slice(0, 10);
      $("#bookDate").value = t;
      $("#bookTime").value = "10:00";
      $("#bookNotes").value = "";
      bookModal.hidden = false;
    }

    bookModal?.addEventListener("click", (e) => {
      if (e.target?.getAttribute?.("data-close") === "1") bookModal.hidden = true;
    });

    doctorDetailModal?.addEventListener("click", (e) => {
      if (e.target?.getAttribute?.("data-close") === "1") doctorDetailModal.hidden = true;
    });

    doctorChatModal?.addEventListener("click", (e) => {
      if (e.target?.getAttribute?.("data-close") === "1") doctorChatModal.hidden = true;
    });

    $("#doctorDetailBookBtn")?.addEventListener("click", () => {
      if (!activeDoctor) return;
      doctorDetailModal.hidden = true;
      openBookModal(activeDoctor.id, activeDoctor.name);
    });

    function appendDoctorChatBubble(role, text) {
      const box = $("#doctorChatWindow");
      if (!box) return;
      const div = document.createElement("div");
      div.className = `bubble ${role}`;
      div.textContent = text;
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
    }

    async function loadDoctorChatHistory(doctorId) {
      const box = $("#doctorChatWindow");
      if (!box) return;
      box.innerHTML = "";
      const items = await api(`/doctor-chat/history/${doctorId}?limit=60`);
      items.forEach((it) => {
        const message = String(it.message || "");
        const cleanedMessage = message.replace(/^\[DoctorChat:\d+\]\s*/, "").replace("__intro__", "").trim();
        if (cleanedMessage) appendDoctorChatBubble("user", cleanedMessage);
        appendDoctorChatBubble("ai", it.response || "");
      });
    }

    async function openDoctorChatModal() {
      if (!activeDoctor) return;
      doctorDetailModal.hidden = true;
      $("#doctorChatTitle").textContent = `Chat with ${formatDoctorDisplayName(activeDoctor.name)}`;
      $("#doctorChatSubtitle").textContent = `${activeDoctor.specialization}`;
      doctorChatModal.hidden = false;
      $("#doctorChatWindow").innerHTML = `<div class="bubble ai">Connecting you with ${escapeHtml(
        formatDoctorDisplayName(activeDoctor.name)
      )}...</div>`;
      await api(`/doctor-chat/start/${activeDoctor.id}`, { method: "POST" });
      await loadDoctorChatHistory(activeDoctor.id);
      $("#doctorChatInput")?.focus();
    }

    $("#doctorDetailChatBtn")?.addEventListener("click", async () => {
      await openDoctorChatModal();
    });

    $("#bookForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const doctor_id = Number($("#bookDoctorId").value);
      const appt_date = $("#bookDate").value;
      const appt_time = $("#bookTime").value;
      const notes = $("#bookNotes").value.trim() || null;
      const bookBtn = $("#bookSubmit");
      setButtonLoading(bookBtn, true, "Booking…");
      try {
        await api("/appointments", {
          method: "POST",
          body: { doctor_id, appt_date, appt_time, notes },
        });
        bookModal.hidden = true;
        toast("Appointment booked", "success");
        await refreshAppointments();
      } catch (err) {
        showAlertBanner(err.message || "Booking failed", "error");
      } finally {
        setButtonLoading(bookBtn, false);
      }
    });

    async function refreshAppointments() {
      const ul = $("#apptList");
      if (!ul) return;
      ul.innerHTML = `<li class="muted">Loading…</li>`;
      try {
        const items = await api("/appointments");
        ul.innerHTML = "";
        if (!items.length) {
          ul.innerHTML = `<li class="muted">No appointments yet. Book from a doctor card.</li>`;
          return;
        }
        items.forEach((a) => {
          const li = document.createElement("li");
          li.innerHTML = `<div>
              <strong>${escapeHtml(a.doctor_name)}</strong>
              <div class="muted small">${escapeHtml(a.specialization)}</div>
              <div class="muted small">${escapeHtml(a.appt_date)} at ${escapeHtml(a.appt_time)}</div>
              <div class="muted small">Status: ${escapeHtml(a.status || "scheduled")}</div>
              ${a.notes ? `<div class="small">${escapeHtml(a.notes)}</div>` : ""}
            </div>
            <button type="button" class="btn ghost small" data-aid="${a.id}">Cancel</button>`;
          ul.appendChild(li);
        });
        ul.querySelectorAll("button[data-aid]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const id = btn.getAttribute("data-aid");
            if (!confirm("Cancel this appointment?")) return;
            try {
              await api(`/appointments/${id}`, { method: "DELETE" });
              toast("Cancelled", "success");
              await refreshAppointments();
            } catch (err) {
              showAlertBanner(err.message || "Could not cancel", "error");
            }
          });
        });
      } catch {
        ul.innerHTML = `<li class="muted">Could not load appointments.</li>`;
      }
    }

    function renderTips() {
      const ul = $("#healthTips");
      const picks = HEALTH_TIPS.slice(0, 3);
      ul.innerHTML = picks.map((t) => `<li>${escapeHtml(t)}</li>`).join("");
    }

    (async () => {
      setPageLoading(true);
      try {
        await refreshProfile();
        await refreshHistory();
        await refreshHealthTable();
        await loadDoctors();
        await refreshAppointments();
      } catch (e) {
        if (e.status === 401) {
          setToken(null);
          window.location.href = "index.html";
          return;
        }
        toast(e.message || "Failed to load dashboard", "error");
      } finally {
        setPageLoading(false);
      }
    })();

    renderTips();

    const today = new Date().toISOString().slice(0, 10);
    $("#healthDate").value = today;

    $("#bmiForm")?.addEventListener("submit", (e) => {
      e.preventDefault();
      const w = Number($("#bmiWeight").value);
      const h = Number($("#bmiHeight").value);
      if (!(w > 0 && h > 0)) return toast("Enter valid weight and height", "error");
      const m = h / 100;
      const bmi = w / (m * m);
      const pill = $("#bmiResult");
      pill.hidden = false;
      pill.textContent = `BMI: ${bmi.toFixed(1)} (${bmiCategory(bmi)})`;
    });

    function bmiCategory(b) {
      if (b < 18.5) return "underweight range (informational)";
      if (b < 25) return "typical range (informational)";
      if (b < 30) return "elevated range (informational)";
      return "higher range (informational)";
    }

    let lastSymptomReport = null;

    function normalizeSymptomInput(raw) {
      const cleaned = String(raw || "")
        .replace(/\s+/g, " ")
        .trim();
      if (!cleaned) return "";
      return cleaned
        .replace(/^(i have|i'm having|i am having|i feel|feeling|suffering from|having)\s+/i, "")
        .replace(/[.,;:!?]+/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 120);
    }

    function doctorMatches(doctorType) {
      const query = String(doctorType || "")
        .toLowerCase()
        .split(/[^a-z]+/)
        .filter(Boolean);
      if (!query.length) return doctorDirectory.slice(0, 3);
      const matches = doctorDirectory.filter((doc) => {
        const text = `${doc.name} ${doc.specialization}`.toLowerCase();
        return query.some((token) => text.includes(token));
      });
      return (matches.length ? matches : doctorDirectory).slice(0, 3);
    }

    async function loadDietSummary() {
      try {
        return await api("/diet-plan");
      } catch {
        return null;
      }
    }

    function renderSymptomResults(symptom, data, dietPlan, doctors) {
      const out = $("#symptomStructured");
      const pdfBtn = $("#downloadReportBtn");
      if (!out) return;
      const dietHtml = dietPlan
        ? `<div class="symptom-card">
            <h4>Diet</h4>
            <p><strong>Recommended:</strong> ${escapeHtml((dietPlan.recommended_foods || []).slice(0, 3).join(", ") || "General balanced meals")}</p>
            <p><strong>Avoid:</strong> ${escapeHtml((dietPlan.foods_to_avoid || []).slice(0, 3).join(", ") || "No specific restrictions")}</p>
          </div>`
        : "";
      const doctorHtml = doctors.length
        ? `<div class="symptom-card">
            <h4>Doctor recommendations</h4>
            <ul>${doctors
              .map((doc) => `<li><strong>${escapeHtml(doc.name)}</strong> — ${escapeHtml(doc.specialization)}</li>`)
              .join("")}</ul>
          </div>`
        : "";
      out.hidden = false;
      out.innerHTML = `
        <div class="symptom-card"><h4>Symptom</h4><p>${escapeHtml(symptom)}</p></div>
        <div class="symptom-card"><h4>Condition (not a diagnosis)</h4><p>${escapeHtml(data.condition)}</p></div>
        <div class="symptom-card"><h4>Doctor</h4><p>${escapeHtml(data.doctor_type)}</p></div>
        ${dietHtml}
        <div class="symptom-card"><h4>Precautions</h4><ul>${(data.precautions || [])
          .map((p) => `<li>${escapeHtml(p)}</li>`)
          .join("")}</ul></div>
        ${doctorHtml}
        <div class="symptom-card"><h4>Disclaimer</h4><p>${escapeHtml(data.disclaimer || "")}</p></div>`;
      lastSymptomReport = {
        symptom,
        condition: data.condition,
        doctor_type: data.doctor_type,
        precautions: data.precautions || [],
        disclaimer: data.disclaimer || "",
      };
      if (pdfBtn) pdfBtn.hidden = false;
    }

    async function downloadHealthSummaryPdf() {
      const btn = $("#downloadReportBtn");
      if (!lastSymptomReport) {
        toast("Run the symptom checker first.", "error");
        return;
      }
      if (btn) btn.disabled = true;
      try {
        const token = getToken();
        const res = await fetch(`${API_BASE}/reports/health-pdf`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(lastSymptomReport),
        });
        if (!res.ok) {
          const errText = await res.text();
          let msg = `Request failed (${res.status})`;
          try {
            const j = JSON.parse(errText);
            msg = formatApiDetail(j.detail) || j.message || msg;
          } catch {
            if (errText) msg = errText.slice(0, 200);
          }
          throw new Error(msg);
        }
        const blob = await res.blob();
        const cd = res.headers.get("Content-Disposition") || "";
        let filename = "health_report.pdf";
        const m = cd.match(/filename="([^"\\]+)"/);
        if (m) filename = m[1];
        const u = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = u;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(u);
        toast("PDF report downloaded", "success");
      } catch (err) {
        toast(err.message || "Download failed", "error");
      } finally {
        if (btn) btn.disabled = false;
      }
    }

    $("#downloadReportBtn")?.addEventListener("click", () => downloadHealthSummaryPdf());

    async function runSymptomAnalysis() {
      const sourceText = chatInput?.value.trim() || "";
      const symptom = normalizeSymptomInput(sourceText);
      const out = $("#symptomStructured");
      const pdfBtn = $("#downloadReportBtn");
      if (!symptom) {
        toast("Enter one symptom in the assistant input first.", "error");
        chatInput?.focus();
        return;
      }
      if (pdfBtn) {
        pdfBtn.hidden = true;
        lastSymptomReport = null;
      }
      setAnalysisLoading(true);
      try {
        if (chatWindow) {
          chatWindow.innerHTML = `<div class="analysis-intro">
            <strong>Analyzing symptom</strong>
            <p>${escapeHtml(sourceText || symptom)}</p>
          </div>`;
        }
        const [data, dietPlan] = await Promise.all([
          api("/symptoms", { method: "POST", body: { symptom } }),
          loadDietSummary(),
        ]);
        const doctors = doctorMatches(data.doctor_type);
        renderSymptomResults(symptom, data, dietPlan, doctors);
        highlightRecommendedDoctors(doctors);
        if (chatWindow) {
          chatWindow.innerHTML = `<div class="analysis-intro">
            <strong>Latest analysis</strong>
            <p><strong>Symptom:</strong> ${escapeHtml(symptom)}</p>
            <p><strong>Condition:</strong> ${escapeHtml(data.condition)}</p>
            <p><strong>Doctor recommendation:</strong> ${escapeHtml(data.doctor_type)}</p>
          </div>`;
        }
        chatInput.value = "";
        await refreshHistory();
        toast("Symptom analysis ready", "success");
      } catch (err) {
        out.hidden = false;
        out.innerHTML = `<p class="form-error">${escapeHtml(err.message || "Failed to analyze.")}</p>`;
        if (chatWindow) {
          chatWindow.innerHTML = `<div class="analysis-intro">
            <strong>Analysis failed</strong>
            <p>${escapeHtml(err.message || "Could not analyze that symptom.")}</p>
          </div>`;
        }
        highlightRecommendedDoctors([]);
        showAlertBanner(err.message || "Symptom check failed", "error");
      } finally {
        setAnalysisLoading(false);
      }
    }

    chatForm?.addEventListener("submit", async (e) => {
      e.preventDefault();
      await runSymptomAnalysis();
    });

    $("#doctorChatForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!activeDoctor) return;
      const input = $("#doctorChatInput");
      const send = $("#doctorChatSend");
      const message = input?.value.trim() || "";
      if (!message) return;
      appendDoctorChatBubble("user", message);
      input.value = "";
      setButtonLoading(send, true, "Sending…");
      try {
        const data = await api("/doctor-chat", {
          method: "POST",
          body: { doctor_id: activeDoctor.id, message },
        });
        appendDoctorChatBubble("ai", data.response || "");
      } catch (err) {
        appendDoctorChatBubble("ai", err.message || "Doctor chat is unavailable right now.");
      } finally {
        setButtonLoading(send, false);
      }
    });

    $("#healthForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const weight_kg = Number($("#healthWeight").value);
      const height_cm = Number($("#healthHeight").value);
      const recorded_date = $("#healthDate").value || undefined;
      const healthBtn = $("#healthSubmit");
      setButtonLoading(healthBtn, true, "Saving…");
      try {
        await api("/health-data", {
          method: "POST",
          body: { weight_kg, height_cm, recorded_date },
        });
        toast("Health entry saved", "success");
        await refreshHealthTable();
        await refreshProfile();
      } catch (err) {
        toast(err.message || "Failed to save", "error");
      } finally {
        setButtonLoading(healthBtn, false);
      }
    });

    const modal = $("#profileModal");
    $("#openProfileEditor")?.addEventListener("click", () => {
      modal.hidden = false;
    });
    modal?.addEventListener("click", (e) => {
      if (e.target?.getAttribute?.("data-close") === "1") modal.hidden = true;
    });
    $("#profileForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const body = {
        name: fd.get("name"),
        age: fd.get("age") ? Number(fd.get("age")) : null,
        weight_kg: fd.get("weight_kg") ? Number(fd.get("weight_kg")) : null,
        height_cm: fd.get("height_cm") ? Number(fd.get("height_cm")) : null,
        medical_history: fd.get("medical_history") || null,
      };
      try {
        await api("/me", { method: "PATCH", body });
        modal.hidden = true;
        toast("Profile updated", "success");
        await refreshProfile();
      } catch (err) {
        toast(err.message || "Update failed", "error");
      }
    });

    const em = $("#emergencyModal");
    $("#emergencyBtn")?.addEventListener("click", async () => {
      const cfg = (await loadPublicConfig()) || {};
      if (!cfg?.hospitals?.length) return;
      const ul = $("#hospitalList");
      ul.innerHTML = cfg.hospitals
        .map(
          (h) =>
            `<li><strong>${escapeHtml(h.name)}</strong> - ${escapeHtml(h.address)} · ${escapeHtml(h.phone)}${
              h.website ? ` · <a href="${escapeHtml(h.website)}" target="_blank" rel="noreferrer">Website</a>` : ""
            }</li>`
        )
        .join("");
    });
    $("#emergencyBtn")?.addEventListener("click", () => {
      const ul = $("#hospitalList");
      ul.innerHTML = SAMPLE_HOSPITALS.map(
        (h) => `<li><strong>${escapeHtml(h.name)}</strong> — ${escapeHtml(h.address)} · ${escapeHtml(h.phone)}</li>`
      ).join("");
      em.hidden = false;
    });
    em?.addEventListener("click", (e) => {
      if (e.target?.getAttribute?.("data-close") === "1") em.hidden = true;
    });

    $("#voiceBtn")?.addEventListener("click", () => {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) {
        toast("Voice input not supported in this browser.", "error");
        return;
      }
      const rec = new SR();
      rec.lang = (navigator.language || "en-US").includes("en") ? navigator.language : "en-US";
      rec.interimResults = false;
      rec.onresult = (ev) => {
        const text = ev.results?.[0]?.[0]?.transcript || "";
        chatInput.value = `${chatInput.value} ${text}`.trim();
      };
      rec.onerror = () => toast("Voice capture error — check microphone permission.", "error");
      rec.start();
      toast("Listening… speak now");
    });
  }

  function adminPage() {
    if (!requireAuth()) return;

    let editingDoctorId = null;
    let editingHospitalId = null;

    $("#logoutBtn")?.addEventListener("click", () => {
      setToken(null);
      window.location.href = "index.html";
    });

    function switchSection(sectionId) {
      $$(".admin-nav-btn").forEach((btn) => {
        const active = btn.dataset.section === sectionId;
        btn.classList.toggle("active", active);
        btn.setAttribute("aria-pressed", String(active));
      });
      $$(".admin-section").forEach((section) => {
        section.hidden = section.id !== sectionId;
      });
    }

    $$(".admin-nav-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchSection(btn.dataset.section));
    });

    function resetDoctorForm() {
      editingDoctorId = null;
      $("#doctorForm")?.reset();
      $("#doctorFormTitle").textContent = "Add doctor";
      $("#doctorSubmitText").textContent = "Save doctor";
      $("#doctorCancelEdit").hidden = true;
    }

    function resetHospitalForm() {
      editingHospitalId = null;
      $("#hospitalForm")?.reset();
      $("#hospitalFormTitle").textContent = "Add hospital";
      $("#hospitalSubmitText").textContent = "Save hospital";
      $("#hospitalCancelEdit").hidden = true;
    }

    async function refreshStats() {
      const stats = await api("/admin/dashboard/stats");
      $("#statUsers").textContent = String(stats.total_users);
      $("#statDoctors").textContent = String(stats.total_doctors);
      $("#statAppointments").textContent = String(stats.total_appointments);
    }

    async function refreshUsers() {
      const users = await api("/admin/users");
      const tbody = $("#usersTable tbody");
      tbody.innerHTML = "";
      users.forEach((user) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${escapeHtml(user.name)}</td>
          <td>${escapeHtml(user.email)}</td>
          <td>
            <select class="admin-select" data-user-role="${user.id}">
              <option value="user"${user.role === "user" ? " selected" : ""}>user</option>
              <option value="admin"${user.role === "admin" ? " selected" : ""}>admin</option>
            </select>
          </td>
          <td><button type="button" class="btn secondary small" data-user-save="${user.id}">Update</button></td>`;
        tbody.appendChild(tr);
      });
      $$("[data-user-save]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const userId = btn.getAttribute("data-user-save");
          const role = $(`[data-user-role="${userId}"]`)?.value || "user";
          try {
            await api(`/admin/users/${userId}`, { method: "PATCH", body: { role } });
            toast("User updated", "success");
            await refreshUsers();
          } catch (err) {
            toast(err.message || "Could not update user", "error");
          }
        });
      });
    }

    async function refreshDoctors() {
      const doctors = await api("/admin/doctors");
      const tbody = $("#doctorsTable tbody");
      tbody.innerHTML = "";
      doctors.forEach((doctor) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><img class="admin-thumb" src="${escapeHtml(doctor.photo_url)}" alt="" /></td>
          <td>${escapeHtml(doctor.name)}</td>
          <td>${escapeHtml(doctor.specialization)}</td>
          <td>${escapeHtml(String(doctor.experience_years))} yrs</td>
          <td class="admin-actions-cell">
            <button type="button" class="btn ghost small" data-doctor-edit="${doctor.id}">Edit</button>
            <button type="button" class="btn danger small" data-doctor-delete="${doctor.id}">Delete</button>
          </td>`;
        tbody.appendChild(tr);
      });

      $$("[data-doctor-edit]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const doctorId = Number(btn.getAttribute("data-doctor-edit"));
          const doctors = await api("/admin/doctors");
          const doctor = doctors.find((item) => item.id === doctorId);
          if (!doctor) return;
          editingDoctorId = doctorId;
          $("#doctorName").value = doctor.name || "";
          $("#doctorSpecialization").value = doctor.specialization || "";
          $("#doctorExperience").value = doctor.experience_years ?? "";
          $("#doctorPhotoUrl").value = doctor.photo_url || "";
          $("#doctorFormTitle").textContent = "Edit doctor";
          $("#doctorSubmitText").textContent = "Update doctor";
          $("#doctorCancelEdit").hidden = false;
          switchSection("doctors");
        });
      });

      $$("[data-doctor-delete]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const doctorId = btn.getAttribute("data-doctor-delete");
          if (!confirm("Delete this doctor?")) return;
          try {
            await api(`/admin/doctors/${doctorId}`, { method: "DELETE" });
            toast("Doctor deleted", "success");
            await refreshDoctors();
            await refreshStats();
          } catch (err) {
            toast(err.message || "Could not delete doctor", "error");
          }
        });
      });
    }

    async function refreshAppointments() {
      const appointments = await api("/admin/appointments");
      const tbody = $("#appointmentsTable tbody");
      tbody.innerHTML = "";
      appointments.forEach((appointment) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${escapeHtml(appointment.user_name)}<div class="muted small">${escapeHtml(appointment.user_email)}</div></td>
          <td>${escapeHtml(appointment.doctor_name)}<div class="muted small">${escapeHtml(appointment.specialization)}</div></td>
          <td>${escapeHtml(appointment.appt_date)}<div class="muted small">${escapeHtml(appointment.appt_time)}</div></td>
          <td>${appointment.notes ? escapeHtml(appointment.notes) : '<span class="muted small">No notes</span>'}</td>
          <td>
            <select class="admin-select" data-appt-status="${appointment.id}">
              ${["scheduled", "confirmed", "completed", "cancelled", "rescheduled"]
                .map(
                  (statusValue) =>
                    `<option value="${statusValue}"${appointment.status === statusValue ? " selected" : ""}>${statusValue}</option>`
                )
                .join("")}
            </select>
          </td>
          <td><button type="button" class="btn secondary small" data-appt-save="${appointment.id}">Save</button></td>`;
        tbody.appendChild(tr);
      });

      $$("[data-appt-save]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const appointmentId = btn.getAttribute("data-appt-save");
          const statusValue = $(`[data-appt-status="${appointmentId}"]`)?.value || "scheduled";
          try {
            await api(`/admin/appointments/${appointmentId}`, {
              method: "PATCH",
              body: { status: statusValue },
            });
            toast("Appointment updated", "success");
            await refreshAppointments();
          } catch (err) {
            toast(err.message || "Could not update appointment", "error");
          }
        });
      });
    }

    async function refreshHospitals() {
      const hospitals = await api("/admin/hospitals");
      const tbody = $("#hospitalsTable tbody");
      tbody.innerHTML = "";
      hospitals.forEach((hospital) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${escapeHtml(hospital.name)}</td>
          <td>${escapeHtml(hospital.address)}</td>
          <td>${escapeHtml(hospital.phone)}</td>
          <td>${hospital.website ? `<a href="${escapeHtml(hospital.website)}" target="_blank" rel="noreferrer">Visit</a>` : '<span class="muted small">-</span>'}</td>
          <td class="admin-actions-cell">
            <button type="button" class="btn ghost small" data-hospital-edit="${hospital.id}">Edit</button>
            <button type="button" class="btn danger small" data-hospital-delete="${hospital.id}">Delete</button>
          </td>`;
        tbody.appendChild(tr);
      });

      $$("[data-hospital-edit]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const hospitalId = Number(btn.getAttribute("data-hospital-edit"));
          const hospitals = await api("/admin/hospitals");
          const hospital = hospitals.find((item) => item.id === hospitalId);
          if (!hospital) return;
          editingHospitalId = hospitalId;
          $("#hospitalName").value = hospital.name || "";
          $("#hospitalAddress").value = hospital.address || "";
          $("#hospitalPhone").value = hospital.phone || "";
          $("#hospitalWebsite").value = hospital.website || "";
          $("#hospitalFormTitle").textContent = "Edit hospital";
          $("#hospitalSubmitText").textContent = "Update hospital";
          $("#hospitalCancelEdit").hidden = false;
          switchSection("hospitals");
        });
      });

      $$("[data-hospital-delete]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const hospitalId = btn.getAttribute("data-hospital-delete");
          if (!confirm("Delete this hospital?")) return;
          try {
            await api(`/admin/hospitals/${hospitalId}`, { method: "DELETE" });
            toast("Hospital deleted", "success");
            await refreshHospitals();
            await loadPublicConfig(true);
          } catch (err) {
            toast(err.message || "Could not delete hospital", "error");
          }
        });
      });
    }

    async function refreshSettings() {
      const settings = await api("/admin/settings");
      $("#settingsApiKey").value = settings.api_key || "";
      $("#settingsEmergencyNumber").value = settings.emergency_number || "";
      $("#settingsFooter").value = settings.footer_text || "";
    }

    async function refreshReports() {
      const reports = await api("/admin/reports");
      const tbody = $("#reportsTable tbody");
      tbody.innerHTML = "";
      reports.forEach((report) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${escapeHtml(report.filename)}</td>
          <td>${escapeHtml(report.user_name)}<div class="muted small">${escapeHtml(report.user_email)}</div></td>
          <td>${escapeHtml(report.report_type)}</td>
          <td>${escapeHtml(new Date(report.created_at).toLocaleString())}</td>
          <td class="admin-actions-cell">
            <button type="button" class="btn ghost small" data-report-view="${report.id}">View</button>
            <button type="button" class="btn secondary small" data-report-download="${report.id}">Download</button>
          </td>`;
        tbody.appendChild(tr);
      });

      $$("[data-report-view]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const reportId = btn.getAttribute("data-report-view");
          try {
            const { blob } = await fetchFileBlob(`/admin/reports/${reportId}/download`);
            const url = URL.createObjectURL(blob);
            window.open(url, "_blank", "noopener,noreferrer");
            setTimeout(() => URL.revokeObjectURL(url), 30000);
          } catch (err) {
            toast(err.message || "Could not open report", "error");
          }
        });
      });

      $$("[data-report-download]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const reportId = btn.getAttribute("data-report-download");
          try {
            const { blob, filename } = await fetchFileBlob(`/admin/reports/${reportId}/download`);
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            toast("Report downloaded", "success");
          } catch (err) {
            toast(err.message || "Could not download report", "error");
          }
        });
      });
    }

    $("#doctorForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        name: $("#doctorName").value.trim(),
        specialization: $("#doctorSpecialization").value.trim(),
        experience_years: Number($("#doctorExperience").value),
        photo_url: $("#doctorPhotoUrl").value.trim(),
      };
      try {
        await api(editingDoctorId ? `/admin/doctors/${editingDoctorId}` : "/admin/doctors", {
          method: editingDoctorId ? "PATCH" : "POST",
          body,
        });
        toast(editingDoctorId ? "Doctor updated" : "Doctor created", "success");
        resetDoctorForm();
        await refreshDoctors();
        await refreshStats();
      } catch (err) {
        toast(err.message || "Could not save doctor", "error");
      }
    });

    $("#doctorCancelEdit")?.addEventListener("click", () => resetDoctorForm());

    $("#hospitalForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        name: $("#hospitalName").value.trim(),
        address: $("#hospitalAddress").value.trim(),
        phone: $("#hospitalPhone").value.trim(),
        website: $("#hospitalWebsite").value.trim() || null,
      };
      try {
        await api(editingHospitalId ? `/admin/hospitals/${editingHospitalId}` : "/admin/hospitals", {
          method: editingHospitalId ? "PATCH" : "POST",
          body,
        });
        toast(editingHospitalId ? "Hospital updated" : "Hospital created", "success");
        resetHospitalForm();
        await refreshHospitals();
        await loadPublicConfig(true);
      } catch (err) {
        toast(err.message || "Could not save hospital", "error");
      }
    });

    $("#hospitalCancelEdit")?.addEventListener("click", () => resetHospitalForm());

    $("#settingsForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api("/admin/settings", {
          method: "PATCH",
          body: {
            api_key: $("#settingsApiKey").value.trim(),
            emergency_number: $("#settingsEmergencyNumber").value.trim(),
            footer_text: $("#settingsFooter").value.trim(),
          },
        });
        await loadPublicConfig(true);
        toast("Settings updated", "success");
      } catch (err) {
        toast(err.message || "Could not update settings", "error");
      }
    });

    (async () => {
      setPageLoading(true);
      try {
        const me = await fetchCurrentUser(true);
        if (!me || me.role !== "admin") {
          window.location.href = "dashboard.html";
          return;
        }
        ensureAdminLinks();
        $("#adminWelcome").textContent = `${me.name} · Admin`;
        switchSection("overview");
        await Promise.all([
          refreshStats(),
          refreshUsers(),
          refreshDoctors(),
          refreshAppointments(),
          refreshHospitals(),
          refreshSettings(),
          refreshReports(),
        ]);
      } catch (err) {
        if (err.status === 401 || err.status === 403) {
          setToken(null);
          window.location.href = "index.html";
          return;
        }
        toast(err.message || "Failed to load admin dashboard", "error");
      } finally {
        setPageLoading(false);
      }
    })();
  }

  async function dietPage() {
    if (!requireAuth()) return;
    const box = $("#dietContent");
    setPageLoading(true);
    try {
      const me = await fetchCurrentUser(true);
      if (me?.role === "admin") ensureAdminLinks();
      const d = await api("/diet-plan");
      box.innerHTML = `
        <section class="diet-block">
          <h2>Recommended foods</h2>
          <ul>${(d.recommended_foods || []).map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
        </section>
        <section class="diet-block">
          <h2>Foods to limit or avoid</h2>
          <ul>${(d.foods_to_avoid || []).map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
        </section>
        <section class="diet-block">
          <h2>Healthy habits</h2>
          <ul>${(d.healthy_habits || []).map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
        </section>
        <section class="diet-block footer-disclaimer" style="margin:0;border-style:dashed">
          <p class="muted small" style="margin:0">${escapeHtml(d.disclaimer || "")}</p>
        </section>`;
    } catch (e) {
      if (e.status === 401) {
        setToken(null);
        window.location.href = "index.html";
        return;
      }
      box.innerHTML = `<p class="form-error">${escapeHtml(e.message || "Could not load diet plan.")}</p>`;
    } finally {
      setPageLoading(false);
    }
  }

  function initFaqAccordion() {
    const acc = $("#faqAccordion");
    if (!acc) return;
    $$(".faq-trigger", acc).forEach((btn) => {
      btn.addEventListener("click", () => {
        const item = btn.closest(".faq-item");
        if (!item) return;
        const wasOpen = item.classList.contains("is-open");
        $$(".faq-item", acc).forEach((it) => {
          it.classList.remove("is-open");
          const b = $(".faq-trigger", it);
          if (b) b.setAttribute("aria-expanded", "false");
        });
        if (!wasOpen) {
          item.classList.add("is-open");
          btn.setAttribute("aria-expanded", "true");
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initFaqAccordion();
    loadPublicConfig();
    const page = window.MEDASSIST_PAGE;
    if (page === "auth") authPage();
    if (page === "dashboard") dashboardPage();
    if (page === "admin") adminPage();
    if (page === "diet") dietPage();
  });
})();
