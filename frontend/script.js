/**
 * frontend/script.js
 * ==================
 * Interactive Client Logic for the GitHub Learning AI Agent.
 * 
 * Connects frontend UI to FastAPI backend:
 * - /chat: Sends questions, renders streaming/agent answers and tool badges
 * - /progress: Loads user's SQLite progress, completed lessons, and skill level
 * - /lessons: Loads the 10-lesson Git & GitHub curriculum
 * - /progress/reset: Resets student progress
 * - /quiz/submit: Evaluates quiz answers and updates scores in SQLite
 */

// Generate or retrieve persistent student session ID
function getSessionId() {
  let sid = localStorage.getItem("github_agent_session_id");
  if (!sid) {
    sid = "student_" + Math.random().toString(36).substring(2, 10) + "_" + Date.now().toString(36);
    localStorage.setItem("github_agent_session_id", sid);
  }
  return sid;
}

const SESSION_ID = getSessionId();

// State management
let lessonsData = [];
let userProgress = {
  current_lesson: 1,
  completed_lessons: [],
  quiz_scores: {},
  skill_level: "Beginner",
  progress_percentage: 0
};
let selectedLessonId = 1;
let selectedQuizOption = null;

// DOM Element References
const lessonListContainer = document.getElementById("lesson-list-container");
const progressBarFill = document.getElementById("progress-bar-fill");
const progressPercentLabel = document.getElementById("progress-percent-label");
const completedCountText = document.getElementById("completed-count-text");
const skillLevelText = document.getElementById("skill-level-text");

const chatFeed = document.getElementById("chat-feed");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const clearChatBtn = document.getElementById("clear-chat-btn");
const quickChips = document.getElementById("quick-chips");
const resetProgressBtn = document.getElementById("reset-progress-btn");

// Lesson Lab Elements
const labLessonNum = document.getElementById("lab-lesson-num");
const labLessonTitle = document.getElementById("lab-lesson-title");
const labLessonDesc = document.getElementById("lab-lesson-desc");
const labExplanation = document.getElementById("lab-explanation");
const labCodeExample = document.getElementById("lab-code-example");
const labTask = document.getElementById("lab-task");
const copyExampleBtn = document.getElementById("copy-example-btn");
const askTaskBtn = document.getElementById("ask-task-btn");

// Quiz Elements
const tabBtnGuide = document.getElementById("tab-btn-guide");
const tabBtnQuiz = document.getElementById("tab-btn-quiz");
const tabPanelGuide = document.getElementById("tab-panel-guide");
const tabPanelQuiz = document.getElementById("tab-panel-quiz");
const tabQuizBadge = document.getElementById("tab-quiz-badge");

const quizQuestionText = document.getElementById("quiz-question-text");
const quizOptionsList = document.getElementById("quiz-options-list");
const submitQuizBtn = document.getElementById("submit-quiz-btn");
const quizFeedbackBox = document.getElementById("quiz-feedback-box");
const feedbackTitle = document.getElementById("feedback-title");
const feedbackBody = document.getElementById("feedback-body");
const quizStatusText = document.getElementById("quiz-status-text");


// ==========================================================================
// INITIALIZATION
// ==========================================================================

document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  await loadLessons();
  await loadProgress();
});


function setupEventListeners() {
  // Chat submit form
  chatForm.addEventListener("submit", handleChatSubmit);

  // Quick prompt chips
  quickChips.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip-btn");
    if (btn && btn.dataset.prompt) {
      chatInput.value = btn.dataset.prompt;
      handleChatSubmit(new Event("submit"));
    }
  });

  // Clear chat
  clearChatBtn.addEventListener("click", () => {
    chatFeed.innerHTML = `
      <div class="message-bubble message-agent welcome-bubble">
        <div class="bubble-header">
          <span class="bubble-sender">GitCoach AI</span>
          <span class="bubble-tag">AGENT READY</span>
        </div>
        <div class="bubble-content">
          <p>Chat feed reset. Ask me any question or request a practical task!</p>
        </div>
      </div>
    `;
  });

  // Reset progress
  resetProgressBtn.addEventListener("click", handleResetProgress);

  // Copy code example
  copyExampleBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(labCodeExample.textContent).then(() => {
      const originalText = copyExampleBtn.textContent;
      copyExampleBtn.textContent = "Copied!";
      setTimeout(() => copyExampleBtn.textContent = originalText, 1800);
    });
  });

  // Ask agent about task
  askTaskBtn.addEventListener("click", () => {
    const lesson = lessonsData.find(l => l.id === selectedLessonId);
    if (lesson) {
      chatInput.value = `I am on Lesson ${lesson.id} (${lesson.title}). Can you guide me through this task: "${lesson.practical_task}"?`;
      handleChatSubmit(new Event("submit"));
    }
  });

  // Lab Tab Switching
  tabBtnGuide.addEventListener("click", () => switchLabTab("guide"));
  tabBtnQuiz.addEventListener("click", () => switchLabTab("quiz"));

  // Submit Quiz Button
  submitQuizBtn.addEventListener("click", handleQuizSubmit);
}


function switchLabTab(tab) {
  if (tab === "guide") {
    tabBtnGuide.classList.add("active");
    tabBtnQuiz.classList.remove("active");
    tabPanelGuide.classList.add("active");
    tabPanelQuiz.classList.remove("active");
  } else {
    tabBtnQuiz.classList.add("active");
    tabBtnGuide.classList.remove("active");
    tabPanelQuiz.classList.add("active");
    tabPanelGuide.classList.remove("active");
  }
}


// ==========================================================================
// API CALLS: LESSONS & PROGRESS
// ==========================================================================

async function loadLessons() {
  try {
    const res = await fetch("/lessons");
    if (!res.ok) throw new Error("Failed to load lessons");
    const data = await res.json();
    lessonsData = data.lessons || [];
    renderLessonList();
    renderLessonLab(selectedLessonId);
  } catch (err) {
    console.error("Error loading lessons:", err);
    lessonListContainer.innerHTML = `<div class="error-state">Error loading curriculum. Please refresh.</div>`;
  }
}

async function loadProgress() {
  try {
    const res = await fetch(`/progress?session_id=${encodeURIComponent(SESSION_ID)}`);
    if (!res.ok) throw new Error("Failed to load progress");
    const data = await res.json();
    userProgress = data;
    updateProgressUI();
  } catch (err) {
    console.error("Error loading progress:", err);
  }
}

function updateProgressUI() {
  // Update progress bar
  const pct = userProgress.progress_percentage || 0;
  progressBarFill.style.width = `${pct}%`;
  progressPercentLabel.textContent = `${pct}%`;
  completedCountText.textContent = `${userProgress.completed_lessons.length} of ${lessonsData.length || 10}`;

  // Update skill level badge
  skillLevelText.textContent = userProgress.skill_level || "Beginner";

  // Re-render lesson list to update checkmarks
  renderLessonList();
  renderQuizStatus(selectedLessonId);
}


// ==========================================================================
// UI RENDERING: CURRICULUM & LESSON LAB
// ==========================================================================

function renderLessonList() {
  if (!lessonsData.length) return;

  lessonListContainer.innerHTML = lessonsData.map((lesson) => {
    const isCompleted = userProgress.completed_lessons.includes(lesson.id);
    const isActive = lesson.id === selectedLessonId;
    const isCurrentInCurriculum = lesson.id === userProgress.current_lesson;

    let itemClasses = ["lesson-item"];
    if (isActive) itemClasses.push("active");
    if (isCompleted) itemClasses.push("completed");

    let statusBadge = "";
    if (isCompleted) {
      statusBadge = `<span class="lesson-status-icon" style="color: var(--color-emerald)">&#10003;</span>`;
    } else if (isCurrentInCurriculum) {
      statusBadge = `<span class="pulse-dot"></span>`;
    }

    return `
      <div class="${itemClasses.join(" ")}" data-lesson-id="${lesson.id}" role="listitem">
        <div class="lesson-num-badge">${lesson.id}</div>
        <div class="lesson-title-text">${lesson.title}</div>
        ${statusBadge}
      </div>
    `;
  }).join("");

  // Attach click events
  lessonListContainer.querySelectorAll(".lesson-item").forEach(item => {
    item.addEventListener("click", () => {
      const id = parseInt(item.dataset.lessonId, 10);
      selectLesson(id);
    });
  });
}

function selectLesson(id) {
  selectedLessonId = id;
  renderLessonList();
  renderLessonLab(id);
}

function renderLessonLab(id) {
  const lesson = lessonsData.find(l => l.id === id);
  if (!lesson) return;

  labLessonNum.textContent = `LESSON ${lesson.id}`;
  labLessonTitle.textContent = lesson.title;
  labLessonDesc.textContent = lesson.description;
  labExplanation.textContent = lesson.explanation;
  labCodeExample.textContent = lesson.example;
  labTask.textContent = lesson.practical_task;

  renderQuizCard(lesson);
}

function renderQuizCard(lesson) {
  selectedQuizOption = null;
  submitQuizBtn.disabled = true;
  quizFeedbackBox.style.display = "none";
  quizFeedbackBox.className = "quiz-feedback";

  const quiz = (lesson.quiz && lesson.quiz[0]) || null;
  if (!quiz) {
    quizQuestionText.textContent = "No quiz currently registered for this lesson.";
    quizOptionsList.innerHTML = "";
    return;
  }

  quizQuestionText.textContent = quiz.question;

  quizOptionsList.innerHTML = quiz.options.map((opt, idx) => `
    <div class="quiz-option" data-option-idx="${idx}">
      <span class="option-indicator"></span>
      <span class="option-text">${opt}</span>
    </div>
  `).join("");

  // Option selection
  quizOptionsList.querySelectorAll(".quiz-option").forEach(optEl => {
    optEl.addEventListener("click", () => {
      quizOptionsList.querySelectorAll(".quiz-option").forEach(el => el.classList.remove("selected"));
      optEl.classList.add("selected");
      selectedQuizOption = parseInt(optEl.dataset.optionIdx, 10);
      submitQuizBtn.disabled = false;
    });
  });

  renderQuizStatus(lesson.id);
}

function renderQuizStatus(lessonId) {
  const isCompleted = userProgress.completed_lessons.includes(lessonId);
  const score = userProgress.quiz_scores ? userProgress.quiz_scores[String(lessonId)] : null;

  if (isCompleted || (score !== undefined && score !== null)) {
    tabQuizBadge.textContent = `${score || 100}% Passed`;
    tabQuizBadge.classList.add("passed");
    quizStatusText.textContent = `Completed (${score || 100}%)`;
    quizStatusText.style.color = "var(--color-emerald)";
  } else {
    tabQuizBadge.textContent = "Pending";
    tabQuizBadge.classList.remove("passed");
    quizStatusText.textContent = "Not Completed";
    quizStatusText.style.color = "var(--text-muted)";
  }
}


// ==========================================================================
// CHAT INTERACTIONS & AGENT CALLING
// ==========================================================================

async function handleChatSubmit(e) {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  chatInput.value = "";
  chatInput.focus();

  // Append user message to UI
  appendUserMessage(text);

  // Show typing bubble
  const typingBubble = appendTypingIndicator();

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: SESSION_ID
      })
    });

    if (!res.ok) {
      throw new Error(`Server returned status ${res.status}`);
    }

    const data = await res.json();

    // Remove typing indicator
    typingBubble.remove();

    // Render assistant message
    appendAgentMessage(data.response, data.tool_called);

    // Update progress state
    if (data.progress) {
      userProgress = data.progress;
      updateProgressUI();
    }
  } catch (err) {
    typingBubble.remove();
    appendAgentMessage(
      `**Error communicating with agent**: ${err.message}. Please verify the FastAPI backend is running.`,
      null
    );
  }
}

function appendUserMessage(text) {
  const msg = document.createElement("div");
  msg.className = "message-bubble message-user";
  msg.innerHTML = `<div class="bubble-content">${escapeHTML(text)}</div>`;
  chatFeed.appendChild(msg);
  requestAnimationFrame(() => {
    chatFeed.scrollTop = chatFeed.scrollHeight;
  });
}

function appendTypingIndicator() {
  const msg = document.createElement("div");
  msg.className = "message-bubble message-agent";
  msg.innerHTML = `
    <div class="bubble-header">
      <span class="bubble-sender">GitCoach AI</span>
      <span class="bubble-tag">REASONING...</span>
    </div>
    <div class="bubble-content">
      <span class="pulse-dot"></span> Agent is thinking and inspecting tools...
    </div>
  `;
  chatFeed.appendChild(msg);
  requestAnimationFrame(() => {
    chatFeed.scrollTop = chatFeed.scrollHeight;
  });
  return msg;
}

function appendAgentMessage(rawText, toolCalled) {
  const msg = document.createElement("div");
  msg.className = "message-bubble message-agent";

  let toolBadgeHTML = "";
  if (toolCalled) {
    toolBadgeHTML = `
      <div class="tool-badge">
        <span>&#128295; Tool Executed:</span>
        <code>${escapeHTML(toolCalled)}</code>
      </div>
    `;
  }

  // Format basic markdown (paragraphs, code blocks, lists, bold)
  const formattedHTML = formatMarkdown(rawText);

  msg.innerHTML = `
    <div class="bubble-header">
      <span class="bubble-sender">GitCoach AI</span>
      <span class="bubble-tag">LANGCHAIN AGENT</span>
    </div>
    ${toolBadgeHTML}
    <div class="bubble-content">
      ${formattedHTML}
    </div>
  `;

  chatFeed.appendChild(msg);
  requestAnimationFrame(() => {
    chatFeed.scrollTop = chatFeed.scrollHeight;
    setTimeout(() => {
      chatFeed.scrollTop = chatFeed.scrollHeight;
    }, 60);
  });
}


// ==========================================================================
// QUIZ SUBMISSION & SCORING
// ==========================================================================

async function handleQuizSubmit() {
  if (selectedQuizOption === null) return;

  submitQuizBtn.disabled = true;
  submitQuizBtn.textContent = "Grading...";

  try {
    const res = await fetch("/quiz/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: SESSION_ID,
        lesson_id: selectedLessonId,
        selected_option: selectedQuizOption
      })
    });

    if (!res.ok) throw new Error("Failed to submit quiz");
    const result = await res.json();

    // Highlight options
    const options = quizOptionsList.querySelectorAll(".quiz-option");
    options.forEach(opt => {
      const idx = parseInt(opt.dataset.optionIdx, 10);
      if (idx === selectedQuizOption) {
        opt.classList.add(result.is_correct ? "correct" : "incorrect");
      }
    });

    // Display feedback box
    quizFeedbackBox.style.display = "block";
    if (result.is_correct) {
      quizFeedbackBox.className = "quiz-feedback success";
      feedbackTitle.textContent = "🎉 Correct! Lesson Mastered (+10%)";
      feedbackBody.textContent = result.explanation;
    } else {
      quizFeedbackBox.className = "quiz-feedback error";
      feedbackTitle.textContent = "❌ Not quite right";
      feedbackBody.textContent = result.explanation + " Try reviewing the lesson guide and attempt again!";
    }

    // Update state & progress
    if (result.progress) {
      userProgress = result.progress;
      updateProgressUI();
    }
  } catch (err) {
    alert("Error submitting quiz: " + err.message);
  } finally {
    submitQuizBtn.textContent = "Check Answer & Record Score";
    submitQuizBtn.disabled = false;
  }
}


// ==========================================================================
// RESET PROGRESS
// ==========================================================================

async function handleResetProgress() {
  if (!confirm("Are you sure you want to reset all your learning progress and quiz scores back to 0%?")) {
    return;
  }

  try {
    const res = await fetch("/progress/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: SESSION_ID })
    });

    if (!res.ok) throw new Error("Failed to reset progress");
    const data = await res.json();
    userProgress = data.progress;
    selectedLessonId = 1;

    updateProgressUI();
    renderLessonLab(1);

    appendAgentMessage(
      "Your learning progress has been reset. We are back at **Lesson 1: Git vs GitHub**! Let me know when you're ready to start.",
      null
    );
  } catch (err) {
    alert("Failed to reset progress: " + err.message);
  }
}


// ==========================================================================
// UTILITY: SIMPLE MARKDOWN & HTML ESCAPING
// ==========================================================================

function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

function formatMarkdown(text) {
  if (!text) return "";

  // 1. Code blocks ```bash ... ```
  let formatted = text.replace(/```([a-z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang}">${escapeHTML(code.trim())}</code></pre>`;
  });

  // 2. Inline code `code`
  formatted = formatted.replace(/`([^`]+)`/g, (match, code) => {
    return `<code>${escapeHTML(code)}</code>`;
  });

  // 3. Bold **text**
  formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // 4. Headers ### Title
  formatted = formatted.replace(/^### (.*$)/gim, '<h4>$1</h4>');
  formatted = formatted.replace(/^## (.*$)/gim, '<h3>$1</h3>');

  // 5. Bullet list items
  formatted = formatted.replace(/^- (.*$)/gim, '<li>$1</li>');
  formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

  // 6. Double newlines to paragraphs
  const paragraphs = formatted.split(/\n\n+/);
  return paragraphs.map(p => {
    p = p.trim();
    if (!p) return "";
    if (p.startsWith("<pre>") || p.startsWith("<h3>") || p.startsWith("<h4>") || p.startsWith("<ul>")) {
      return p;
    }
    return `<p>${p.replace(/\n/g, "<br>")}</p>`;
  }).join("");
}
