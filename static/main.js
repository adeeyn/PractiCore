function togglePassword(id) {
    const input = document.getElementById(id);

    if (input) {
        input.type = input.type === "password" ? "text" : "password";
    }
}

document.addEventListener('DOMContentLoaded', () => {
  const passwordIcon = document.getElementById('password-icon');
  const passwordInput = document.getElementById('passwordInput'); 

  if (passwordIcon && passwordInput) {
    passwordIcon.addEventListener('click', () => {
      const isPassword = passwordInput.type === 'password';
      
      
      passwordInput.type = isPassword ? 'text' : 'password';
      
      
      passwordIcon.src = isPassword 
        ? passwordIcon.dataset.hideSrc 
        : passwordIcon.dataset.viewSrc;
    });
  }
});


function setRole(button) {
    document.querySelectorAll(".role-switch button").forEach(btn => {
        btn.classList.remove("active");
    });

    button.classList.add("active");
}

function switchToEmployer(event) {
    event.preventDefault();

    const buttons = document.querySelectorAll(".role-switch button");

    buttons.forEach(btn => {
        btn.classList.remove("active");
    });

    if (buttons[1]) {
        buttons[1].classList.add("active");
    }
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
    window.location.href = "/student_login";
}

document.addEventListener("DOMContentLoaded", function () {
    const errorMessage = document.getElementById("login-error");

    if (errorMessage) {
        const params = new URLSearchParams(window.location.search);

        if (params.get("failed") === "1") {
            errorMessage.textContent = "Incorrect username or password. Try again!";
        }
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const errorMessage = document.getElementById("login-error");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");

    const params = new URLSearchParams(window.location.search);

    if (params.get("failed") === "1") {
        errorMessage.textContent = "Incorrect username or password. Try again!";

        if (passwordInput) {
            passwordInput.value = "";
        }

        setTimeout(function () {
            window.history.replaceState(
                {},
                document.title,
                "/student_login"
            );
        }, 100);
    }
});