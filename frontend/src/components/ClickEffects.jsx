import { useEffect } from "react";

export default function ClickEffects() {
  useEffect(() => {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("pointer-glow-canvas");
    svg.setAttribute("aria-hidden", "true");

    const defs = document.createElementNS(svg.namespaceURI, "defs");
    const gradient = document.createElementNS(svg.namespaceURI, "linearGradient");
    gradient.id = "pointer-trail-gradient";
    gradient.setAttribute("gradientUnits", "userSpaceOnUse");
    [
      ["0%", "#ff3b30", "0"],
      ["16%", "#ff9500", ".8"],
      ["33%", "#ffeb3b", ".85"],
      ["50%", "#34c759", ".9"],
      ["66%", "#00c7ff", ".9"],
      ["83%", "#5856d6", ".9"],
      ["100%", "#bf5af2", ".9"],
    ].forEach(([offset, color, opacity]) => {
      const stop = document.createElementNS(svg.namespaceURI, "stop");
      stop.setAttribute("offset", offset);
      stop.setAttribute("stop-color", color);
      stop.setAttribute("stop-opacity", opacity);
      gradient.append(stop);
    });
    defs.append(gradient);

    const trail = document.createElementNS(svg.namespaceURI, "path");
    trail.setAttribute("fill", "none");
    trail.setAttribute("stroke", "url(#pointer-trail-gradient)");
    trail.setAttribute("stroke-width", "5");
    trail.setAttribute("stroke-linecap", "round");
    trail.setAttribute("stroke-linejoin", "round");
    svg.append(defs, trail);
    document.body.append(svg);

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const points = [];
    let animationFrame = 0;
    let lastMoveAt = 0;

    const updateTrail = (now) => {
      animationFrame = 0;
      const recent = points.filter((point) => now - point.time < 220);
      if (recent.length < 2) {
        trail.setAttribute("d", "");
        svg.style.opacity = "0";
        return;
      }

      const path = recent
        .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
        .join(" ");
      trail.setAttribute("d", path);
      const last = recent[recent.length - 1];
      const first = recent[0];
      gradient.setAttribute("x1", String(first.x));
      gradient.setAttribute("y1", String(first.y));
      gradient.setAttribute("x2", String(last.x));
      gradient.setAttribute("y2", String(last.y));

      const idleTime = now - lastMoveAt;
      svg.style.opacity = String(Math.max(0.18, 1 - idleTime / 400));
      animationFrame = window.requestAnimationFrame(updateTrail);
    };

    const hidePointerGlow = () => {
      points.length = 0;
      trail.setAttribute("d", "");
      svg.style.opacity = "0";
      if (animationFrame) window.cancelAnimationFrame(animationFrame);
      animationFrame = 0;
    };

    const handlePointerMove = (event) => {
      if (event.pointerType && event.pointerType !== "mouse") {
        hidePointerGlow();
        return;
      }
      const now = performance.now();
      const previous = points[points.length - 1];
      const distance = previous ? Math.hypot(event.clientX - previous.x, event.clientY - previous.y) : Infinity;
      if (!previous || distance >= 2) {
        points.push({ x: event.clientX, y: event.clientY, time: now });
        if (points.length > 18) points.shift();
      }
      lastMoveAt = now;
      if (!animationFrame) {
        animationFrame = window.requestAnimationFrame(updateTrail);
      }
    };

    const handlePointerDown = (event) => {
      if (event.button !== 0 || reducedMotion.matches) return;
      const effect = document.createElement("span");
      effect.className = "click-effect";
      effect.style.left = `${event.clientX}px`;
      effect.style.top = `${event.clientY}px`;
      effect.addEventListener("animationend", () => effect.remove(), { once: true });
      document.body.append(effect);
    };

    document.addEventListener("pointermove", handlePointerMove, { passive: true });
    document.addEventListener("pointerdown", handlePointerDown, { passive: true });
    document.addEventListener("pointercancel", hidePointerGlow, { passive: true });
    window.addEventListener("blur", hidePointerGlow);
    document.documentElement.addEventListener("pointerleave", hidePointerGlow);

    return () => {
      document.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("pointercancel", hidePointerGlow);
      window.removeEventListener("blur", hidePointerGlow);
      document.documentElement.removeEventListener("pointerleave", hidePointerGlow);
      if (animationFrame) window.cancelAnimationFrame(animationFrame);
      svg.remove();
    };
  }, []);

  return null;
}
