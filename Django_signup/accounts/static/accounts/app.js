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

const signupForm = document.querySelector("#signup-form");

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
