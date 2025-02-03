document.addEventListener("DOMContentLoaded", () => {
  const tasksList = document.getElementById("tasks");
  const form = document.getElementById("form");
  const taskInput = document.getElementById("taskInput");

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const taskText = taskInput.value.trim();
    if (taskText === "") return;

    const taskItem = document.createElement("li");
    taskItem.textContent = taskText;

    const deleteButton = document.createElement("button");
    deleteButton.textContent = "❌";
    deleteButton.classList.add("delete");
    deleteButton.addEventListener("click", () => {
      tasksList.removeChild(taskItem);
    });

    taskItem.appendChild(deleteButton);
    tasksList.appendChild(taskItem);

    taskInput.value = "";
  });
});
