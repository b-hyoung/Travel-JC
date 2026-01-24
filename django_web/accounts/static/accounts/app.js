const animated = document.querySelectorAll("[data-animate]");
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (prefersReducedMotion) {
  animated.forEach((el) => el.classList.add("is-visible"));
} else {
  animated.forEach((el, index) => {
    window.setTimeout(() => {
      el.classList.add("is-visible");
    }, 120 * index);
  });
}

const body = document.body;
if (body) {
  const isAuthenticated = body.dataset.authenticated === "1";
  const rememberMe = body.dataset.rememberMe === "1";
  const leftKey = "jc_left_site";
  const internalNavKey = "jc_internal_nav";

  if (!isAuthenticated || rememberMe) {
    try {
      localStorage.removeItem(leftKey);
      sessionStorage.removeItem(internalNavKey);
    } catch (err) {}
  } else {
    try {
      const leftFlag = localStorage.getItem(leftKey);
      let allowListeners = true;
      if (leftFlag) {
        localStorage.removeItem(leftKey);
        let sameOriginReferrer = false;
        if (document.referrer) {
          try {
            sameOriginReferrer =
              new URL(document.referrer).origin === window.location.origin;
          } catch (err) {}
        }
        if (!sameOriginReferrer) {
          window.location.replace("/logout/");
          allowListeners = false;
        }
      }
      if (allowListeners) {
        const markInternalNav = () => {
          try {
            sessionStorage.setItem(internalNavKey, "1");
          } catch (err) {}
        };

        document.addEventListener(
          "click",
          (event) => {
            const link = event.target.closest("a");
            if (!link) return;
            const href = link.getAttribute("href");
            if (!href || href.startsWith("#")) return;
            if (link.target && link.target !== "_self") return;
            let url;
            try {
              url = new URL(href, window.location.href);
            } catch (err) {
              return;
            }
            if (url.origin === window.location.origin) {
              markInternalNav();
            }
          },
          true,
        );

        document.addEventListener(
          "submit",
          (event) => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement)) return;
            const action = form.getAttribute("action") || window.location.href;
            let url;
            try {
              url = new URL(action, window.location.href);
            } catch (err) {
              return;
            }
            if (url.origin === window.location.origin) {
              markInternalNav();
            }
          },
          true,
        );

        window.addEventListener("pagehide", () => {
          let internal = false;
          try {
            internal = sessionStorage.getItem(internalNavKey) === "1";
            sessionStorage.removeItem(internalNavKey);
          } catch (err) {
            internal = false;
          }
          if (!internal) {
            try {
              localStorage.setItem(leftKey, String(Date.now()));
            } catch (err) {}
          }
        });

        window.addEventListener("pageshow", () => {
          try {
            sessionStorage.removeItem(internalNavKey);
          } catch (err) {}
        });
      }
    } catch (err) {}
  }
}

const successMessages = document.querySelectorAll(".message.success");
if (successMessages.length > 0) {
  window.setTimeout(() => {
    successMessages.forEach((message) => {
      message.classList.add("is-hidden");
      window.setTimeout(() => {
        message.remove();
      }, 250);
    });
  }, 2000);
}

const signupForm = document.querySelector("#signup-form");

const progressFilterInputs = document.querySelectorAll(
  'input[name="progress-filter"]',
);

const applyProgressFilters = () => {
  if (progressFilterInputs.length === 0) return;
  const active = Array.from(progressFilterInputs).find((input) => input.checked);
  const filter = active ? active.id.replace("filter-", "") : "all";

  const toggleItems = (selector, startClass, spotClass) => {
    const items = document.querySelectorAll(selector);
    items.forEach((item) => {
      const isStart = item.classList.contains(startClass);
      const isSpot = item.classList.contains(spotClass);
      const show =
        filter === "all" ||
        (filter === "start" && isStart) ||
        (filter === "spot" && isSpot);
      item.classList.toggle("is-hidden", !show);
    });
  };

  toggleItems(
    ".progress-view--simple .stamp-item",
    "stamp-item--start",
    "stamp-item--spot",
  );
  toggleItems(
    ".progress-view--detail .spot-item",
    "spot-item--start",
    "spot-item--spot",
  );
};

if (progressFilterInputs.length > 0) {
  progressFilterInputs.forEach((input) => {
    input.addEventListener("change", applyProgressFilters);
  });
  applyProgressFilters();
}

if (signupForm) {
  const passwordInput =
    signupForm.querySelector("#password") || signupForm.querySelector("#id_password1");
  const confirmInput =
    signupForm.querySelector("#confirm-password") || signupForm.querySelector("#id_password2");
  const formMessage = document.querySelector("#form-message");
  const matchStatus = document.querySelector("[data-match]");
  const ruleItems = document.querySelectorAll(".password-hints li");
  const matchText = matchStatus?.dataset.matchText || "Match";
  const mismatchText = matchStatus?.dataset.mismatchText || "No match";
  const errLength = formMessage?.dataset.errorLength || "Password must be 1-10 characters.";
  const errBoth = formMessage?.dataset.errorBoth || "Include letters and numbers.";
  const errEmpty = formMessage?.dataset.errorEmpty || "Enter password.";

  const rules = {
    length: (value) => value.length > 0 && value.length <= 10,
    number: (value) => /[0-9]/.test(value),
    letter: (value) => /[A-Za-z]/.test(value),
  };

  const setMessage = (text, type) => {
    if (!formMessage) return;
    formMessage.textContent = text;
    formMessage.classList.remove("is-success", "is-error");
    if (type) {
      formMessage.classList.add(type);
    }
  };

  const updateRules = (value) => {
    ruleItems.forEach((item) => {
      const rule = item.dataset.rule;
      const valid = rules[rule] ? rules[rule](value) : false;
      item.classList.toggle("is-valid", valid);
    });
  };

  const updateMatch = () => {
    if (!passwordInput || !confirmInput || !matchStatus) return;
    const password = passwordInput.value;
    const confirmation = confirmInput.value;

    if (!confirmation) {
      matchStatus.textContent = "";
      matchStatus.classList.remove("is-match", "is-mismatch");
      return;
    }

    if (password === confirmation) {
      matchStatus.textContent = matchText;
      matchStatus.classList.add("is-match");
      matchStatus.classList.remove("is-mismatch");
    } else {
      matchStatus.textContent = mismatchText;
      matchStatus.classList.add("is-mismatch");
      matchStatus.classList.remove("is-match");
    }
  };

  passwordInput?.addEventListener("input", (event) => {
    updateRules(event.target.value);
    updateMatch();
  });

  confirmInput?.addEventListener("input", updateMatch);

  signupForm.addEventListener("submit", (event) => {
    if (passwordInput && confirmInput) {
      if (passwordInput.value.length === 0 || confirmInput.value.length === 0) {
        event.preventDefault();
        setMessage(errEmpty, "is-error");
        return;
      }
      if (passwordInput.value.length > 10 || confirmInput.value.length > 10) {
        event.preventDefault();
        setMessage(errLength, "is-error");
        return;
      }
      if (passwordInput.value !== confirmInput.value) {
        event.preventDefault();
        setMessage(mismatchText, "is-error");
        return;
      }
      if (!/[0-9]/.test(passwordInput.value) || !/[A-Za-z]/.test(passwordInput.value)) {
        event.preventDefault();
        setMessage(errBoth, "is-error");
        return;
      }
    }

    setMessage("잠시만 기다려주세요...", "is-success");
  });
}

const routeModal = document.querySelector("#route-modal");
if (routeModal) {
  const modalTitle = routeModal.querySelector("[data-route-modal-title]");
  const modalBody = routeModal.querySelector("[data-route-modal-body]");
  const modalCloseTargets = routeModal.querySelectorAll("[data-route-modal-close]");
  const routeCards = document.querySelectorAll(".route-card");
  const moreText =
    routeModal.dataset.routeMoreText || "Details";
  const lessText =
    routeModal.dataset.routeLessText || "Hide";

  const openRouteModal = (card) => {
    if (!modalTitle || !modalBody || !card) return;
    const index = card.dataset.routeIndex;
    if (index === undefined) return;
    const template = document.querySelector(`#route-detail-${index}`);
    if (!template) return;
    modalTitle.textContent = card.querySelector(".route-title")?.textContent || "";
    modalBody.innerHTML = template.innerHTML;
    const legs = modalBody.querySelectorAll(".route-detail-leg");
    legs.forEach((leg) => {
      const toggle = leg.querySelector("[data-route-toggle]");
      const options = leg.querySelector("[data-route-options]");
      if (!toggle || !options) return;
      options.hidden = true;
      leg.classList.remove("is-open");
      toggle.textContent = moreText;
      toggle.setAttribute("aria-expanded", "false");
    });
    routeModal.classList.add("is-open");
    document.body.classList.add("is-modal-open");
    routeModal.setAttribute("aria-hidden", "false");
  };

  const closeRouteModal = () => {
    routeModal.classList.remove("is-open");
    document.body.classList.remove("is-modal-open");
    routeModal.setAttribute("aria-hidden", "true");
  };

  routeCards.forEach((card) => {
    card.addEventListener("click", () => openRouteModal(card));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openRouteModal(card);
      }
    });
  });

  modalBody?.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-route-toggle]");
    if (!toggle) return;
    const leg = toggle.closest(".route-detail-leg");
    const options = leg?.querySelector("[data-route-options]");
    if (!leg || !options) return;
    const isHidden = options.hidden;
    options.hidden = !isHidden;
    leg.classList.toggle("is-open", isHidden);
    toggle.textContent = isHidden ? lessText : moreText;
    toggle.setAttribute("aria-expanded", isHidden ? "true" : "false");
  });

  modalCloseTargets.forEach((target) => {
    target.addEventListener("click", closeRouteModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && routeModal.classList.contains("is-open")) {
      closeRouteModal();
    }
  });
}
