document.addEventListener("DOMContentLoaded", () => {
  const tasksList = document.getElementById("tasks");
  const form = document.getElementById("form");
  const taskInput = document.getElementById("taskInput");
  const logoutButton = document.getElementById("logoutButton");

  const socket = io();

  // przycisk wylogowania
  if (logoutButton) {
    logoutButton.addEventListener("click", function () {
      window.location.href = "/logout"; // Przekierowanie na /logout
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault(); // zapobiegamy domyślnemu przeładowaniu strony

    const taskText = taskInput.value.trim();
    if (taskText === "") return;

    // wysyłamy żądanie POST do backendu, aby dodać nowe zadanie
    fetch("/todos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: taskText }),
    })
      .then((response) => response.json())
      .then((newTask) => {
        taskInput.value = "";
      })
      .catch((error) => console.error("Error adding task:", error));
  });

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

    taskItem.appendChild(textSpan);
    taskItem.appendChild(buttonsContainer);
    tasksList.appendChild(taskItem);
  }

  function removeTaskFromDOM(taskId) {
    const taskItem = document.getElementById(`task-${taskId}`);
    if (taskItem) {
      taskItem.remove();
    }
  }

  // funkcja pobierająca wszystkie zadania z backendu
  function loadTasks() {
    fetch("/todos")
      .then((response) => response.json())
      .then((tasks) => {
        tasksList.innerHTML = ""; // Czyścimy listę
        tasks.forEach((task) => addTaskToDOM(task));
      })
      .catch((error) => console.error("Error loading tasks:", error));
  }

  // nasłuchiwanie zdarzenia "todo created" z backendu
  socket.on("todo created", (task) => {
    if (!document.getElementById(`task-${task.id}`)) {
      addTaskToDOM(task);
    }
  });

  // nasłuchiwanie zdarzenia "todo deleted" z backendu
  socket.on("todo deleted", (task) => {
    removeTaskFromDOM(task.id);
  });

  // pobieramy zadania z backendu po załadowaniu strony
  loadTasks();
});
