const DIARY_VIEW_KEY_FORM = document.getElementById('diary-view-key-form');
const DIARY_VIEW_KEY_FORM_INPUT = document.getElementById('diary-view-key-form-input');
const DIARY_SUBMIT_KEY_FORM = document.getElementById('diary-submit-key-form');
const DIARY_SUBMIT_KEY_FORM_INPUT = document.getElementById('diary-submit-key-form-input');

function handleDiaryViewKeyFormSubmission(event) {
    event.preventDefault();

    const diaryKey = DIARY_VIEW_KEY_FORM_INPUT.value;

    if (diaryKey) {
        localStorage.setItem('DIARY_VIEW_KEY', diaryKey);
        alert('Diary View Key has been stored!');
    } else {
        alert('Please enter a valid key.');
    }
}
function handleDiarySubmitKeyFormSubmission(event) {
    event.preventDefault();

    const diaryKey = DIARY_SUBMIT_KEY_FORM_INPUT.value;

    if (diaryKey) {
        localStorage.setItem('DIARY_SUBMIT_KEY', diaryKey);
        alert('Diary Submit Key has been stored!');
    } else {
        alert('Please enter a valid key.');
    }
}
// Execution begins
DIARY_VIEW_KEY_FORM_INPUT.value = localStorage.getItem('DIARY_VIEW_KEY');
DIARY_SUBMIT_KEY_FORM_INPUT.value = localStorage.getItem('DIARY_SUBMIT_KEY');

DIARY_VIEW_KEY_FORM.addEventListener('submit', handleDiaryViewKeyFormSubmission);
DIARY_SUBMIT_KEY_FORM.addEventListener('submit', handleDiarySubmitKeyFormSubmission);