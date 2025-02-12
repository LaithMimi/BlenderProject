let userPreferences = {};

// Show popup on load
document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("popup").style.display = "flex";
});

// Save preferences
function savePreferences() {
  const name = document.getElementById('name').value.trim();
  const level = document.getElementById('level').value;
  const week = document.getElementById('week').value;
  const gender = document.getElementById('gender').value;
  const language = document.getElementById('language').value;

  if (!name || !level || !week || !gender || !language) {
    alert("Please fill out all preferences.");
    return;
  }

  userPreferences = { name, level, week, gender, language };
  console.log("Selected preferences =>", userPreferences);

  // Hide popup
  document.getElementById("popup").style.display = "none";

  // Show chat window
  document.getElementById("chatContainer").style.display = "flex";

  // Display welcome message in the selected language
  const welcomeText = getWelcomeMessage(userPreferences.language, userPreferences.name);
  appendBotMessage(welcomeText);

  // Scroll to bottom of chat box
  const chatBox = document.getElementById('chat-box');
  chatBox.scrollTop = chatBox.scrollHeight;
}

function getWelcomeMessage(language, name) {
  switch (language) {
    case 'arabic':
      return `مرحبًا ${name}! كيف بقدر اساعدك اليوم؟`;
    case 'transliteration-hebrew':
      return `מרחבא ${name}! כיף בקדר אסאעדכ אליום?`;
    case 'transliteration-english':
      return `Marhaba ${name}! Kaif bakdar asadak alyom?`;
    default:
      return `Hello ${name}! How can I help you today?`;
  }
}

// Send message
function sendMessage() {
  const userInputElement = document.getElementById('user-input');
  const userInput = userInputElement.value.trim();
  if (!userInput) return;

  // Display user message
  appendUserMessage(userInput);

  // Clear input
  userInputElement.value = '';

  // Send the question to the backend
  fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      level: userPreferences.level,
      week: userPreferences.week,
      question: userInput,
      gender: userPreferences.gender,
      language: userPreferences.language
    })
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to connect to the backend.');
      }
      return response.json();
    })
    .then(data => {
      // Display bot's message
      appendBotMessage(data.answer);
      const chatBox = document.getElementById('chat-box');
      chatBox.scrollTop = chatBox.scrollHeight;
    })
    .catch(error => {
      // Display error message in popup
      showErrorPopup("Sorry, I couldn't connect to the backend. Please try again later.");
      console.error('Error sending message:', error);
    });
}

function appendUserMessage(message) {
  const chatBox = document.getElementById('chat-box');
  const userMessageDiv = document.createElement('div');
  userMessageDiv.className = 'chat-message user-message';

  const userTextSpan = document.createElement('span');
  userTextSpan.className = 'user-text';
  userTextSpan.textContent = message;

  userMessageDiv.appendChild(userTextSpan);
  chatBox.appendChild(userMessageDiv);

  // Scroll to bottom
  chatBox.scrollTop = chatBox.scrollHeight;
}

function appendBotMessage(message) {
  const botMessage = document.createElement('div');
  botMessage.className = 'bot-message';
  const botIcon = document.createElement('span');
  botIcon.className = 'bot-icon';
  botIcon.textContent = '🤖';
  const messageText = document.createElement('p');
  messageText.textContent = message;
  botMessage.appendChild(botIcon);
  botMessage.appendChild(messageText);
  document.getElementById('chat-box').appendChild(botMessage);
}

// Display error message
function showErrorPopup(message) {
  const errorPopup = document.getElementById('error-popup');
  const errorMessage = document.getElementById('error-message');
  errorMessage.textContent = message;
  errorPopup.style.display = 'flex';
}

// Close error popup
function closeErrorPopup() {
  document.getElementById('error-popup').style.display = 'none';
}

// Theme toggle
document.getElementById('theme-toggle').addEventListener('click', function () {
  document.body.classList.toggle('dark-mode');
  const isDarkMode = document.body.classList.contains('dark-mode');
  localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
});

// Load saved theme
function loadTheme() {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') {
    document.body.classList.add('dark-mode');
  }
}

// Open Contact Form
function openContactForm() {
  document.getElementById("contact-popup").style.display = "flex";
}

// Close Contact Form
function closeContactForm() {
  document.getElementById("contact-popup").style.display = "none";
}

// Handle Contact Form Submission
document.getElementById("contact-form").addEventListener("submit", function (event) {
  event.preventDefault();

  const name = document.getElementById("contact-name").value.trim();
  const email = document.getElementById("contact-email").value.trim();
  const message = document.getElementById("contact-message").value.trim();

  if (!name || !email || !message) {
    alert("Please fill out all fields in the contact form.");
    return;
  }

  // Example: Send form data to the server
  console.log("Contact Form Submitted:", { name, email, message });

  // Show success message
  alert("Thank you for contacting us! We will get back to you soon.");

  // Close the contact form
  closeContactForm();
});

// Initialize
loadTheme();

// Function to handle sending message with Enter key
const chatInput = document.getElementById('user-input');
chatInput.addEventListener('keypress', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

// Send message when clicking the send button
document.getElementById('send-button').addEventListener('click', sendMessage);
