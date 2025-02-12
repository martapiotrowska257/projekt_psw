document.addEventListener("DOMContentLoaded", () => {
  const sessionList = document.getElementById("sessionsList");
  const createPrivateSessionBtn = document.getElementById("newPrivateSession");
  const createGroupSessionBtn = document.getElementById("newGroupSession");
  const logoutButton = document.getElementById("logoutButton");

  const socket = io();

  if (!sessionList) {
    console.error("Brak elementu sessionsList w DOM.");
    return;
  }

  // Pobieranie dostępnych sesji
  function loadSessions() {
    fetch("/sessions")
      .then((response) => response.json())
      .then((sessions) => {
        sessionList.innerHTML = "";
        sessions.forEach((session) => addSessionToDOM(session));
      })
      .catch((error) => console.error("Error loading sessions:", error));
  }

  // Dodawanie sesji do DOM
  function addSessionToDOM(session) {
    const sessionItem = document.createElement("li");
    sessionItem.textContent = `${session.name} (${session.type})`;

    const joinButton = document.createElement("button");
    joinButton.textContent = "Dołącz";
    joinButton.addEventListener("click", () => joinSession(session.id));

    sessionItem.appendChild(joinButton);
    sessionList.appendChild(sessionItem);
  }

  // Tworzenie nowej sesji
  function createSession(type) {
    fetch("/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type }),
    })
      .then((response) => response.json())
      .then((newSession) => {
        addSessionToDOM(newSession);
      })
      .catch((error) => console.error("Error creating session:", error));
  }

  // Dołączanie do sesji
  function joinSession(sessionId) {
    fetch(`/sessions/${sessionId}/join`, { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          window.location.href = "/tasks";
        } else {
          alert("Nie udało się dołączyć do sesji.");
        }
      })
      .catch((error) => {
        console.error("Error joining session:", error);
        alert("Wystąpił błąd podczas dołączania do sesji.");
      });
  }

  // Obsługa przycisków tworzenia sesji
  createPrivateSessionBtn.addEventListener("click", () =>
    createSession("private")
  );
  createGroupSessionBtn.addEventListener("click", () => createSession("group"));

  // Obsługa wylogowania
  logoutButton.addEventListener("click", () => {
    fetch("/logout", { method: "POST" })
      .then(() => {
        window.location.href = "/login";
      })
      .catch((error) => console.error("Error logging out:", error));
  });

  // Załaduj sesje po otwarciu strony
  loadSessions();
});
