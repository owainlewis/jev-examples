document.querySelectorAll("form[data-busy]").forEach((form) => {
  form.addEventListener("submit", () => {
    form.querySelector("button[type=submit]").disabled = true;
    form.querySelector(".busy").textContent = form.dataset.busy;
  });
});
