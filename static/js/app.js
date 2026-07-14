const state = {
  currentTrainer: null,
  chats: {},
  appointmentType: "personal",
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 3000);
}

function openDialog(dialog) {
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function closeDialog(dialog) {
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

$("#menuToggle").addEventListener("click", () => $("#topNav").classList.toggle("open"));
$$("#topNav a").forEach(link => link.addEventListener("click", () => $("#topNav").classList.remove("open")));

$("#changeGym").addEventListener("click", () => $("#selectedGym").focus());

function syncSelectedGym() {
  const selected = $("#selectedGym").selectedOptions[0];
  if (!selected) return;
  $("#selectedGymAddress").textContent = `⌖ ${selected.dataset.address}`;
  $("#gymFilter").value = selected.value;
  filterClasses();
}

$("#selectedGym").addEventListener("change", syncSelectedGym);
$("#inviteButton").addEventListener("click", () => showToast("Enlace de invitación copiado · demo"));

function filterClasses() {
  const gym = $("#gymFilter").value;
  const activity = $("#activityFilter").value;
  let visible = 0;
  $$(".class-card").forEach(card => {
    const matchesGym = gym === "all" || card.dataset.gym === gym;
    const matchesActivity = activity === "all" || card.dataset.activity === activity;
    const show = matchesGym && matchesActivity;
    card.hidden = !show;
    if (show) visible += 1;
  });
  $("#emptyClasses").hidden = visible !== 0;
}
$("#gymFilter").addEventListener("change", filterClasses);
$("#activityFilter").addEventListener("change", filterClasses);

const enrollModal = $("#enrollModal");
$$(".enroll-trigger").forEach(button => {
  button.addEventListener("click", event => {
    event.stopPropagation();
    $("#enrollClassId").value = button.dataset.classId;
    $("#enrollTitle").textContent = `Inscribirse a ${button.dataset.className}`;
    $("#enrollMeta").textContent = `${button.dataset.classGym} · ${button.dataset.classAddress} · ${button.dataset.classTime}`;
    $("#enrollStatus").textContent = "";
    openDialog(enrollModal);
  });
});

$("#enrollForm").addEventListener("submit", async event => {
  event.preventDefault();
  const status = $("#enrollStatus");
  status.classList.remove("error");
  status.textContent = "Confirmando...";
  try {
    const response = await fetch("/api/classes/enroll", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        class_id: $("#enrollClassId").value,
        member_name: $("#enrollName").value.trim(),
        email: $("#enrollEmail").value.trim(),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "No se pudo completar la inscripción");
    const spots = document.querySelector(`[data-spots-for="${data.enrollment.class_id}"]`);
    if (spots) spots.textContent = data.remaining_spots;
    status.textContent = data.message;
    showToast(data.message);
    window.setTimeout(() => closeDialog(enrollModal), 1100);
  } catch (error) {
    status.classList.add("error");
    status.textContent = error.message;
  }
});

const appointmentModal = $("#appointmentModal");
function openAppointment(type, preferredTrainer = null) {
  state.appointmentType = type;
  $("#appointmentTitle").textContent = type === "diet" ? "Reservar consulta con dietista" : "Reservar entrenamiento personal";
  const options = $$("#professionalId option");
  options.forEach(option => {
    const isDiet = option.dataset.role === "Dietista";
    option.hidden = type === "diet" ? !isDiet : isDiet;
  });
  const visibleOption = preferredTrainer
    ? options.find(option => option.value === preferredTrainer && !option.hidden)
    : options.find(option => !option.hidden);
  if (visibleOption) $("#professionalId").value = visibleOption.value;
  const selectedGym = $("#selectedGym").value;
  if (selectedGym) $("#appointmentGym").value = selectedGym;
  $("#appointmentStatus").textContent = "";
  $("#appointmentDate").min = new Date().toISOString().split("T")[0];
  openDialog(appointmentModal);
}
$$('[data-open-appointment]').forEach(button => button.addEventListener("click", () => openAppointment(button.dataset.openAppointment)));

$("#appointmentForm").addEventListener("submit", async event => {
  event.preventDefault();
  const status = $("#appointmentStatus");
  status.classList.remove("error");
  status.textContent = "Confirmando...";
  try {
    const response = await fetch("/api/appointments", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        professional_id: $("#professionalId").value,
        gym_id: $("#appointmentGym").value,
        member_name: $("#appointmentName").value.trim(),
        email: $("#appointmentEmail").value.trim(),
        service: state.appointmentType === "diet" ? "Consulta con dietista" : "Entrenamiento personal",
        appointment_date: $("#appointmentDate").value,
        appointment_time: $("#appointmentTime").value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "No se pudo completar la reserva");
    status.textContent = data.message;
    showToast(data.message);
    window.setTimeout(() => closeDialog(appointmentModal), 1200);
  } catch (error) {
    status.classList.add("error");
    status.textContent = error.message;
  }
});

$$('[data-close-modal]').forEach(button => button.addEventListener("click", () => closeDialog($("#" + button.dataset.closeModal))));
$$('dialog').forEach(dialog => dialog.addEventListener("click", event => {
  const rect = dialog.getBoundingClientRect();
  const outside = event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom;
  if (outside) closeDialog(dialog);
}));

function appendMessage(text, type) {
  const message = document.createElement("div");
  message.className = `message ${type}`;
  message.textContent = text;
  $("#chatMessages").appendChild(message);
  $("#chatMessages").scrollTop = $("#chatMessages").scrollHeight;
  return message;
}

function openChat(card) {
  const trainer = {
    id: card.dataset.trainerId,
    name: card.dataset.trainerName,
    role: card.dataset.trainerRole,
    specialty: card.dataset.trainerSpecialty,
    image: card.dataset.trainerImage,
    greeting: card.dataset.trainerGreeting,
  };
  state.currentTrainer = trainer;
  state.chats[trainer.id] ||= [{type: "bot", text: trainer.greeting}];
  $("#chatAvatar").src = trainer.image;
  $("#chatAvatar").alt = `Foto de ${trainer.name}`;
  $("#chatName").textContent = trainer.name;
  $("#chatRole").textContent = `${trainer.role} · ${trainer.specialty}`;
  const messages = $("#chatMessages");
  messages.innerHTML = "";
  state.chats[trainer.id].forEach(item => appendMessage(item.text, item.type));
  $("#chatWidget").hidden = false;
  $("#chatWidget").classList.remove("minimized");
  $("#chatInput").focus();
}
$$(".trainer-card").forEach(card => {
  card.addEventListener("click", event => {
    if (event.target.closest("video")) return;
    openChat(card);
  });
  card.addEventListener("keydown", event => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    openChat(card);
  });
});

$("#closeChat").addEventListener("click", () => $("#chatWidget").hidden = true);
$("#minimizeChat").addEventListener("click", () => {
  const widget = $("#chatWidget");
  const isMinimized = widget.dataset.minimized === "true";
  widget.dataset.minimized = String(!isMinimized);
  $("#chatMessages").hidden = !isMinimized;
  $("#quickReplies").hidden = !isMinimized;
  $("#chatForm").hidden = !isMinimized;
  $("#minimizeChat").textContent = isMinimized ? "−" : "+";
});

async function sendChatMessage(text) {
  if (!state.currentTrainer || !text.trim()) return;
  const trainer = state.currentTrainer;
  state.chats[trainer.id].push({type: "user", text});
  appendMessage(text, "user");
  const typing = appendMessage("Escribiendo…", "bot typing");
  try {
    const response = await fetch(`/api/chat/${trainer.id}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: text}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "No se pudo responder");
    typing.remove();
    state.chats[trainer.id].push({type: "bot", text: data.reply});
    appendMessage(data.reply, "bot");
  } catch (error) {
    typing.textContent = "No he podido responder. Inténtalo de nuevo.";
    typing.classList.remove("typing");
  }
}

$("#chatForm").addEventListener("submit", event => {
  event.preventDefault();
  const input = $("#chatInput");
  const text = input.value.trim();
  input.value = "";
  sendChatMessage(text);
});
$$("#quickReplies button").forEach(button => button.addEventListener("click", () => sendChatMessage(button.textContent)));

// Abrir por defecto a Laura para enseñar la capacidad de diálogo del mockup.
window.addEventListener("load", () => {
  const laura = document.querySelector('[data-trainer-id="laura"]');
  if (laura && window.innerWidth > 1100) openChat(laura);
});
