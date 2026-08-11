export function createPandaMascot(className = "") {
  const mascot = document.createElement("span");
  mascot.className = ["panda-mascot", className].filter(Boolean).join(" ");
  mascot.setAttribute("aria-hidden", "true");
  return mascot;
}
