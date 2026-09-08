import './copy.js';

const walkthrough = document.querySelector('.walkthrough');
const steps = [...document.querySelectorAll('.step')];
const next = document.querySelector('#next-step');
const sourceDetails = document.querySelector('#source-details');
const sourceSheet = document.querySelector('#source-sheet');
let currentStep = 0;
let question = 'date';

const stageCopy = [
  {
    title: 'Every memory starts somewhere.',
    description: 'On September 1, the team records a launch date. This is a useful note—but it is only one piece of the story.',
    explanation: 'Dates are part of the source text. A retrieval score alone does not tell you whether a fact is current.',
    action: 'Reveal the update',
  },
  {
    title: 'The plan moves. Keep the context.',
    description: 'A week later, the team records a new date and a reason. The update is a separate, explicitly linked note. The first note stays available.',
    explanation: 'These are two retained documents, not automatic revision history. The connection is supplied with the notes.',
    action: 'Ask a question',
  },
  {
    title: 'Ask for the pieces that matter.',
    description: 'A question can retrieve evidence from both notes. Select a prepared example to see how their context helps a reader interpret the change.',
    explanation: 'This local walkthrough uses fixed examples. TESSERA returns structured evidence; your agent reasons with it.',
    action: 'Follow the evidence',
  },
  {
    title: 'A useful result has a way back.',
    description: 'Follow either source below. The excerpt stays connected to its document, while the original note remains available for inspection.',
    explanation: 'Exact spans are returned only when provable. Relevance, source authority and temporal validity are different questions.',
    action: 'Start again',
  },
];

const questions = {
  date: {
    label: 'When is the Atlas launch?',
    before: 'The update names ',
    emphasis: 'September 26',
    after: '. The first note records September 12.',
  },
  change: {
    label: 'What changed in the launch plan?',
    before: 'The update moves launch from September 12 to September 26 to ',
    emphasis: 'finish accessibility testing',
    after: '.',
  },
};

function setQuestion(value, announce = true) {
  question = value;
  const copy = questions[value];
  document.querySelector('#selected-question').textContent = copy.label;
  const emphasis = document.createElement('strong');
  emphasis.textContent = copy.emphasis;
  document.querySelector('#result-copy').replaceChildren(copy.before, emphasis, copy.after);
  document.querySelectorAll('[data-question]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.question === question));
  });
  if (announce) document.querySelector('#demo-announcement').textContent = `${copy.label} Reader interpretation: ${copy.before}${copy.emphasis}${copy.after}`;
}

function setSource(value, open = false) {
  const isLater = value === 'later';
  document.querySelector('#sheet-path').textContent = isLater ? 'atlas/launch-update.md' : 'atlas/launch-plan.md';
  document.querySelector('#sheet-quote').textContent = isLater
    ? 'September 8, 2026. The Atlas launch is moved to September 26 to finish accessibility testing.'
    : 'September 1, 2026. The Atlas launch is scheduled for September 12.';
  document.querySelector('#sheet-detail').textContent = isLater
    ? 'This update explicitly links to atlas/launch-plan. Both documents remain available; the relationship does not itself prove which statement is current.'
    : 'A separate Markdown note, retained as context. The dates here are written by the fictional team.';
  document.querySelectorAll('.source-tabs button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.source === value)));
  if (open) sourceDetails.open = true;
}

function setStep(value) {
  currentStep = value;
  const copy = stageCopy[value];
  walkthrough.dataset.step = String(value);
  steps.forEach((button, index) => {
    if (index === value) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  });
  document.querySelector('#step-title').textContent = copy.title;
  document.querySelector('#step-description').textContent = copy.description;
  document.querySelector('#step-explanation p').textContent = copy.explanation;
  next.firstChild.textContent = `${copy.action} `;
  next.lastElementChild.textContent = value === 3 ? '↺' : '→';
  document.querySelector('#context-counter').textContent = value === 0 ? 'One source in view' : 'Two sources in view';
  document.querySelector('#later-note').hidden = value === 0;
  document.querySelector('#note-placeholder').hidden = value !== 0;
  document.querySelector('#later-source-button').hidden = value === 0;
  document.querySelector('#relation-line').hidden = value === 0;
  document.querySelector('#question-picker').hidden = value < 2;
  document.querySelector('#retrieved-note').hidden = value < 2;
  setSource(value === 0 ? 'earlier' : 'later');
  sourceDetails.open = value === 3;
  if (value === 0) setQuestion('date', false);
  const animated = value === 1 ? document.querySelector('#later-note') : document.querySelector('#retrieved-note');
  // Replacing the animation object keeps work confined to deliberate state changes.
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches && !animated.hidden) {
    animated.animate([{ opacity: 0.4, transform: 'translateY(7px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 220, easing: 'ease-out' });
  }
  document.querySelector('#demo-announcement').textContent = `Step ${value + 1} of 4. ${copy.title} ${copy.description}`;
}

steps.forEach(button => button.addEventListener('click', () => setStep(Number(button.dataset.step))));
next.addEventListener('click', () => setStep((currentStep + 1) % 4));
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => setQuestion(button.dataset.question)));
document.querySelectorAll('[data-source]').forEach(control => control.addEventListener('click', event => {
  event.preventDefault();
  setSource(control.dataset.source, true);
  if (control.matches('a')) {
    sourceSheet.scrollIntoView({ block: 'nearest', behavior: 'instant' });
    sourceSheet.focus({ preventScroll: true });
  }
}));

