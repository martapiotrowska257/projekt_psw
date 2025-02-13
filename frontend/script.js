document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form");

  const sessionList = document.getElementById("sessionList");
  const newSessionButton = document.getElementById("newSessionButton");

  const tasksList = document.getElementById("tasks");
  const taskInput = document.getElementById("taskInput");
  const logoutButton = document.getElementById("logoutButton");

  // const io = require("socket.io-client");
  // const socket = io("wss://localhost:5000");

  // przycisk wylogowania
  if (logoutButton) {
    logoutButton.addEventListener("click", function () {
      window.location.href = "/logout"; // Przekierowanie na /logout
    });
  }

  if (form && taskInput) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const taskText = taskInput.value.trim();
      if (!taskText) return;

      fetch("/todos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: taskText }),
      })
        .then((response) => response.json())
        .then((newTask) => {
          taskInput.value = "";
          addTaskToDOM(newTask);
        })
        .catch((error) => console.error("Error adding task:", error));
    });
  }

  // pobieranie listy sesji
  function loadSessions() {
    if (!sessionList) return;
    fetch("/sessionslist", {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    })
      .then((response) => response.json())
      .then((sessions) => {
        sessionList.innerHTML = "";
        sessions.forEach((session) => addSessionToDOM(session));
      })
      .catch((error) => console.error("Error loading sessions:", error));
  }

  // tworzenie nowej sesji
  function createSession(sessionName, type) {
    if (!sessionName) return;

    fetch("/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: sessionName, type: type }),
    })
      .then((response) => response.json())
      .then((newSession) => {
        addSessionToDOM(newSession);
      })
      .catch((error) => console.error("Error creating session:", error));
  }

  // dodawanie sesji do DOM
  function addSessionToDOM(session) {
    const li = document.createElement("li");
    li.textContent = `${session.name} (${session.is_private}) `;

    const selectButton = document.createElement("button");
    selectButton.textContent = "Select Session";
    selectButton.addEventListener("click", () => {
      if (session.type === "group") {
        // For group sessions, send a join request first.
        // joinSession(session.id);
      } else {
        // For private sessions, simply redirect.
        window.location.href = `/todos`;
      }
    });
    li.appendChild(selectButton);

    sessionList.appendChild(li);
  }

  // dołączanie do sesji
  function joinSession(sessionId) {
    fetch(`/sessions/${sessionId}/join`, { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          window.location.href = `/todos?session_id=${sessionId}`;
        } else {
          alert("Nie udało się dołączyć do sesji.");
        }
      })
      .catch((error) => {
        console.error("Error joining session:", error);
        alert("Wystąpił błąd podczas dołączania do sesji.");
      });
  }

  if (newSessionButton) {
    newSessionButton.addEventListener("click", (e) => {
      e.preventDefault();
      const sessionNameInput = document.getElementById("session_name");
      const sessionTypeInput = document.getElementById("session_type");

      if (sessionNameInput && sessionTypeInput) {
        const sessionName = sessionNameInput.value.trim();
        const sessionType = sessionTypeInput.value.trim();
        createSession(sessionName, sessionType);
      }
    });
  }

  function addTaskToDOM(task) {
    const taskItem = document.createElement("li");
    taskItem.id = `task-${task.id}`;

    const textSpan = document.createElement("span");
    textSpan.textContent = `${task.title}`;

    if (task.completed) {
      textSpan.classList.add("completed");
    }

    // kontener na przycisk zmiany stanu zadania i przycisk usuwania zadania
    const buttonsContainer = document.createElement("div");
    buttonsContainer.classList.add("buttons");

    // przycisk przełączający stan zadania
    const toggleButton = document.createElement("button");
    toggleButton.textContent = task.completed ? "Mark as undone" : "✅";
    toggleButton.classList.add("toggle");

    // dodajemy obsługę kliknięcia przycisku – wysyłamy żądanie PUT do backendu, aby zaktualizować pole "completed"
    toggleButton.addEventListener("click", () => {
      fetch(`/todos/${task.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ completed: !task.completed }),
      })
        .then((response) => response.json())
        .then((updatedTask) => {
          if (updatedTask.completed) {
            textSpan.classList.add("completed");
            toggleButton.textContent = "Mark as undone";
          } else {
            textSpan.classList.remove("completed");
            toggleButton.textContent = "✅";
          }
          task.completed = updatedTask.completed;
        })
        .catch((error) => console.error("Error updating task:", error));
    });

    const deleteButton = document.createElement("button");
    deleteButton.textContent = "❌";
    deleteButton.classList.add("delete");

    // dodajemy obsługę kliknięcia przycisku – wysyłamy żądanie DELETE do backendu
    deleteButton.addEventListener("click", () => {
      fetch(`/todos/${task.id}`, { method: "DELETE" })
        .then((response) => response.json())
        .then((deletedTask) => {
          removeTaskFromDOM(deletedTask.id);
        })
        .catch((error) => console.error("Error deleting task:", error));
    });

    buttonsContainer.appendChild(toggleButton);
    buttonsContainer.appendChild(deleteButton);

    tasksList.appendChild(taskItem);
    taskItem.appendChild(textSpan);
    taskItem.appendChild(buttonsContainer);
  }

  function removeTaskFromDOM(taskId) {
    const taskItem = document.getElementById(`task-${taskId}`);
    if (taskItem) {
      taskItem.remove();
    }
  }

  // funkcja pobierająca wszystkie zadania z backendu
  function loadTasks() {
    if (!tasksList) return;
    fetch("/todoslist")
      .then((response) => response.json())
      .then((tasks) => {
        tasksList.innerHTML = ""; // Czyścimy listę
        tasks.forEach((task) => addTaskToDOM(task));
      })
      .catch((error) => console.error("Error loading tasks:", error));
  }

  // // nasłuchiwanie zdarzenia "todo created" z backendu
  // socket.on("todo created", (task) => {
  //   if (!document.getElementById(`task-${task.id}`)) {
  //     addTaskToDOM(task);
  //   }
  // });

  // // nasłuchiwanie zdarzenia "todo deleted" z backendu
  // socket.on("todo deleted", (task) => {
  //   removeTaskFromDOM(task.id);
  // });

  // pobieramy zadania z backendu po załadowaniu strony
  loadSessions();
  loadTasks();
});
