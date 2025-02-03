document.addEventListener("DOMContentLoaded", () => {
  const tasksList = document.getElementById("tasks");
  const form = document.getElementById("form");
  const taskInput = document.getElementById("taskInput");

  const socket = io();

  form.addEventListener("submit", (event) => {
    event.preventDefault(); // zapobiegamy domyślnemu przeładowaniu strony

    const taskText = taskInput.value.trim();
    if (taskText === "") return;

    // Wysyłanie żądania POST do backendu, aby dodać nowe zadanie
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
    taskItem.textContent = `${task.id}. ${task.title}`;

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

    taskItem.appendChild(deleteButton);
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
        // Wyczyść listę zadań przed dodaniem pobranych elementów
        tasksList.innerHTML = "";
        tasks.forEach((task) => addTaskToDOM(task));
      })
      .catch((error) => console.error("Error loading tasks:", error));
  }

  // nasłuchiwanie zdarzenia "todo created" z backendu
  socket.on("todo created", (task) => {
    // Dodajemy zadanie do DOM, jeśli jeszcze go tam nie ma
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
