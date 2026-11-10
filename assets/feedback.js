// PORTABLE FEEDBACK WIDGET
// Smile / frown buttons that open a Survey123 feedback form in an in-page modal.
//
// WHY SURVEY123 IN A MODAL: these apps embed in ArcGIS Experience Builder, whose
// iframe is sandboxed without allow-top-navigation/allow-popups — so mailto and
// new-tab links are hard-blocked. A Survey123 web form loaded into a child iframe
// renders in-page (no navigation), submits to a hosted layer in Jeff's AGOL org
// (durable, org-owned, survives any one person), and can email on submit. Nothing
// for anyone to maintain but the survey itself.
//
// To reuse in another app: copy the buttons, the CSS block, and this file; then
// set SURVEY_URL below to that app's Survey123 web-form share URL.
(function () {
  "use strict";

  // Survey123 web-form share URL. floridaros -> "Florida ROS Feedback" (public).
  var SURVEY_URL = "https://survey123.arcgis.com/share/0db36bff549740e9a35c880fc70bc04f"; // "App Feedback" (Jeff-only) — default for non-Florida apps

  // Which app this feedback came from. Prefilled (hidden) into the survey's "app"
  // field so a shared survey can tell apps apart in the Feedback Inbox. Set this
  // per app when reusing the widget.
  var APP_NAME = "dylan"; // e.g. "atlas", "sitaware" — shows/filters in the Feedback Inbox

  // Default (collect) mode opens a blank form ready to submit. hideNavBar = clean
  // embed. field:app / field:page_url prefill hidden questions (ignored by a
  // survey that doesn't have them, so it is always safe to send).
  function formSrc() {
    return SURVEY_URL +
      "?hideNavBar=true" +
      "&field:app=" + encodeURIComponent(APP_NAME) +
      "&field:page_url=" + encodeURIComponent(location.href);
  }

  var overlay = null;

  function closeModal() {
    if (overlay) {
      overlay.parentNode && overlay.parentNode.removeChild(overlay);
      overlay = null;
      document.removeEventListener("keydown", onKey);
    }
  }

  function onKey(e) {
    if (e.key === "Escape") closeModal();
  }

  function openModal(mood) {
    closeModal();
    var isUp = mood === "up";

    overlay = document.createElement("div");
    overlay.className = "feedback-overlay";
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeModal();
    });

    var card = document.createElement("div");
    card.className = "feedback-modal feedback-modal--survey";
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "true");
    card.setAttribute("aria-label", "Send feedback");

    card.innerHTML =
      '<div class="feedback-modal-head">' +
      "<strong>" + (isUp ? "What do you like?" : "What could be better?") + "</strong>" +
      '<button type="button" class="feedback-modal-close" aria-label="Close">×</button>' +
      "</div>" +
      '<iframe class="feedback-survey" title="Feedback form" ' +
      'src="' + formSrc() + '" ' +
      'allow="clipboard-write; geolocation"></iframe>' +
      '<p class="feedback-modal-hint">' +
      "Can't see the form? <a href=\"" + SURVEY_URL + "\" target=\"_blank\" rel=\"noopener\">open it in a new tab</a>." +
      "</p>";

    overlay.appendChild(card);
    document.body.appendChild(overlay);
    document.addEventListener("keydown", onKey);
    card.querySelector(".feedback-modal-close").addEventListener("click", closeModal);
  }

  function wire() {
    var buttons = document.querySelectorAll("[data-feedback]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener("click", function (e) {
        e.preventDefault();
        openModal(this.getAttribute("data-feedback"));
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
