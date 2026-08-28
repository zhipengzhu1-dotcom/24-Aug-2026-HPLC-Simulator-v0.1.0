// Reusable retrieval-practice quiz widget for the HPLC teaching workspace.
//
// Markup contract (see any lesson for a worked example):
//
// <div class="quiz" data-correct="b">
//   <div class="q-prompt">Question text…</div>
//   <div class="q-options">
//     <label class="q-option"><input type="radio" value="a"> option text</label>
//     <label class="q-option"><input type="radio" value="b"> option text</label>
//   </div>
//   <button class="q-check">Check</button>
//   <div class="q-feedback" data-correct-text="…" data-incorrect-text="…"></div>
// </div>
//
// No answer key ships to the reader in cleartext beyond data-correct on the
// container — fine for a personal teaching workspace, not meant to resist
// view-source. Each quiz gets its own radio-group name so multiple quizzes
// on one page don't cross-wire.
(function () {
  function init() {
    var quizzes = document.querySelectorAll(".quiz");
    quizzes.forEach(function (quiz, i) {
      var groupName = "quiz-" + i;
      quiz.querySelectorAll('input[type="radio"]').forEach(function (input) {
        input.name = groupName;
      });
      var button = quiz.querySelector(".q-check");
      var feedback = quiz.querySelector(".q-feedback");
      if (!button || !feedback) return;
      button.addEventListener("click", function () {
        var picked = quiz.querySelector('input[type="radio"]:checked');
        if (!picked) {
          feedback.className = "q-feedback show incorrect";
          feedback.textContent = "Pick an option first.";
          return;
        }
        var correct = picked.value === quiz.getAttribute("data-correct");
        feedback.className = "q-feedback show " + (correct ? "correct" : "incorrect");
        var text = correct
          ? feedback.getAttribute("data-correct-text") || "Correct."
          : feedback.getAttribute("data-incorrect-text") || "Not quite — try again.";
        feedback.textContent = (correct ? "✓ " : "✗ ") + text;
      });
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
