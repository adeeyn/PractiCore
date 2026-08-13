
function togglePassword(id) {
  const input = document.getElementById(id);
  if (input) input.type = input.type === "password" ? "text" : "password";
}

function setRole(button) {
  document.querySelectorAll(".role-switch button").forEach(btn => btn.classList.remove("active"));
  button.classList.add("active");
}

function switchToEmployer(event) {
  event.preventDefault();
  const buttons = document.querySelectorAll(".role-switch button");
  buttons.forEach(btn => btn.classList.remove("active"));
  if (buttons[1]) buttons[1].classList.add("active");
}

function login(event) {
  event.preventDefault();
  window.location.href = "student_dashboard.html";
}

function registerUser(event) {
  event.preventDefault();
  const password = document.getElementById("password").value;
  const confirm = document.getElementById("confirmPassword").value;

  if (password !== confirm) {
    alert("Passwords do not match.");
    return;
  }
  alert("Account created successfully.");
  window.location.href = "login.html";
}
