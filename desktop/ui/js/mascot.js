export function createPandaMascot(className = "") {
  const mascot = document.createElement("span");
  mascot.className = ["panda-mascot", className].filter(Boolean).join(" ");
  mascot.setAttribute("aria-hidden", "true");
  hydratePandaMascot(mascot);
  return mascot;
}

export function setPandaReaction(mascot, reaction = "") {
  if (!mascot) return mascot;
  if (reaction) {
    mascot.dataset.pandaReaction = reaction;
  } else {
    delete mascot.dataset.pandaReaction;
  }
  return mascot;
}

export function hydratePandaMascot(mascot) {
  if (!mascot || mascot.dataset.pandaReady === "1") return mascot;
  mascot.dataset.pandaReady = "1";

  const stage = document.createElement("span");
  stage.className = "panda-stage";

  [
    "panda-leg left",
    "panda-leg right",
    "panda-body",
    "panda-belly",
    "panda-arm left",
    "panda-arm right",
    "panda-paw left",
    "panda-paw right",
    "panda-ear left",
    "panda-ear right",
    "panda-face",
    "panda-muzzle",
    "panda-eye left",
    "panda-eye right",
    "panda-shine left",
    "panda-shine right",
    "panda-brow left",
    "panda-brow right",
    "panda-nose",
    "panda-mouth",
    "panda-cheek left",
    "panda-cheek right",
  ].forEach((className) => {
    const part = document.createElement("span");
    part.className = className;
    stage.append(part);
  });

  mascot.append(stage);

  mascot.addEventListener("pointerenter", () => setPandaReaction(mascot, "curious"));
  mascot.addEventListener("pointerleave", () => setPandaReaction(mascot));
  mascot.addEventListener("pointerdown", () => setPandaReaction(mascot, "happy"));
  mascot.addEventListener("pointerup", () => setPandaReaction(mascot, "curious"));

  return mascot;
}
