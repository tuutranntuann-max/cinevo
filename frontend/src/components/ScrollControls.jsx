import { useEffect, useRef, useState } from "react";

function overflowOn(element, axis) {
  if (!element || element === document.documentElement || element === document.body) {
    return false;
  }
  const style = window.getComputedStyle(element);
  if (axis === "x") {
    return /auto|scroll|overlay/.test(style.overflowX)
      && element.scrollWidth > element.clientWidth + 1;
  }
  return /auto|scroll|overlay/.test(style.overflowY)
    && element.scrollHeight > element.clientHeight + 1;
}

function findScrollable(element, axis) {
  for (let node = element; node && node !== document.body; node = node.parentElement) {
    if (overflowOn(node, axis)) return node;
  }
  return window;
}

function findFirstHorizontalScrollable() {
  return [...document.querySelectorAll("body *")].find((element) => overflowOn(element, "x")) || window;
}

function getHorizontalPosition(target) {
  if (target === window) {
    const root = document.documentElement;
    return {
      position: window.scrollX,
      maximum: root.scrollWidth - window.innerWidth,
    };
  }
  return {
    position: target.scrollLeft,
    maximum: target.scrollWidth - target.clientWidth,
  };
}

function Arrow({ direction }) {
  const paths = {
    left: "m15 18-6-6 6-6",
    right: "m9 18 6-6-6-6",
  };
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d={paths[direction]} />
    </svg>
  );
}

export default function ScrollControls() {
  const horizontalTarget = useRef(window);
  const controlsRef = useRef(null);
  const dragRef = useRef(null);
  const [canScroll, setCanScroll] = useState({ left: false, right: false });
  const [position, setPosition] = useState(null);

  useEffect(() => {
    const updateControls = () => {
      let horizontal = horizontalTarget.current;
      if (horizontal !== window && (!horizontal.isConnected || !overflowOn(horizontal, "x"))) {
        horizontal = window;
      }
      if (
        horizontal === window
        && document.documentElement.scrollWidth <= window.innerWidth + 1
      ) {
        horizontal = findFirstHorizontalScrollable();
      }
      horizontalTarget.current = horizontal;

      const x = getHorizontalPosition(horizontal);
      const next = {
        left: x.position > 1,
        right: x.maximum - x.position > 1,
      };
      setCanScroll((current) => (
        current.left === next.left
        && current.right === next.right
          ? current
          : next
      ));
    };

    const hideNativeScrollbars = () => {
      const root = document.documentElement;
      const elements = [root, document.body, ...root.querySelectorAll("*")];
      elements.forEach((element) => {
        const x = element === root || element === document.body
          ? root.scrollWidth > window.innerWidth + 1
          : overflowOn(element, "x");
        const y = element === root || element === document.body
          ? root.scrollHeight > window.innerHeight + 1
          : overflowOn(element, "y");
        element.classList.toggle("app-scrollbar-hidden", x || y);
      });
    };

    let scanFrame = 0;
    const scheduleScrollbarScan = () => {
      cancelAnimationFrame(scanFrame);
      scanFrame = requestAnimationFrame(() => {
        hideNativeScrollbars();
        updateControls();
      });
    };

    const setTargetsFromPointer = (event) => {
      if (event.target.closest?.(".app-scroll-controls")) return;
      const horizontal = findScrollable(event.target, "x");
      if (horizontal === window) return;
      if (horizontalTarget.current === horizontal) return;
      horizontalTarget.current = horizontal;
      updateControls();
    };
    const setTargetsFromFocus = (event) => {
      if (event.target.closest?.(".app-scroll-controls")) return;
      const horizontal = findScrollable(event.target, "x");
      if (horizontal === window) return;
      horizontalTarget.current = horizontal;
      updateControls();
    };
    const onScroll = () => updateControls();
    const observer = new MutationObserver(scheduleScrollbarScan);

    observer.observe(document.documentElement, { childList: true, subtree: true });
    document.addEventListener("pointermove", setTargetsFromPointer, true);
    document.addEventListener("focusin", setTargetsFromFocus, true);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", scheduleScrollbarScan);
    scheduleScrollbarScan();

    return () => {
      cancelAnimationFrame(scanFrame);
      observer.disconnect();
      document.removeEventListener("pointermove", setTargetsFromPointer, true);
      document.removeEventListener("focusin", setTargetsFromFocus, true);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", scheduleScrollbarScan);
      document.querySelectorAll(".app-scrollbar-hidden")
        .forEach((element) => element.classList.remove("app-scrollbar-hidden"));
    };
  }, []);

  function scroll(amount) {
    const target = horizontalTarget.current;
    if (target === window) {
      window.scrollBy({ left: amount, behavior: "smooth" });
    } else {
      target.scrollBy({ left: amount, behavior: "smooth" });
    }
  }

  function keepInsideViewport(x, y) {
    const controls = controlsRef.current;
    if (!controls) return { x, y };
    return {
      x: Math.max(0, Math.min(x, window.innerWidth - controls.offsetWidth)),
      y: Math.max(0, Math.min(y, window.innerHeight - controls.offsetHeight)),
    };
  }

  function startDragging(event) {
    const bounds = controlsRef.current.getBoundingClientRect();
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: bounds.left,
      originY: bounds.top,
    };
    setPosition({ x: bounds.left, y: bounds.top });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function drag(event) {
    const start = dragRef.current;
    if (!start || start.pointerId !== event.pointerId) return;
    setPosition(keepInsideViewport(
      start.originX + event.clientX - start.startX,
      start.originY + event.clientY - start.startY,
    ));
  }

  function stopDragging(event) {
    if (dragRef.current?.pointerId === event.pointerId) dragRef.current = null;
  }

  function moveWithKeyboard(event) {
    const offsets = {
      ArrowLeft: [-20, 0],
      ArrowRight: [20, 0],
      ArrowUp: [0, -20],
      ArrowDown: [0, 20],
    };
    const offset = offsets[event.key];
    if (!offset) return;
    event.preventDefault();
    const bounds = controlsRef.current.getBoundingClientRect();
    setPosition(keepInsideViewport(
      (position?.x ?? bounds.left) + offset[0],
      (position?.y ?? bounds.top) + offset[1],
    ));
  }

  const buttons = [
    { direction: "left", amount: -500, disabled: !canScroll.left },
    { direction: "right", amount: 500, disabled: !canScroll.right },
  ];

  return (
    <nav
      ref={controlsRef}
      className="app-scroll-controls"
      aria-label="Điều hướng cuộn trang"
      style={position ? { left: position.x, top: position.y, right: "auto", bottom: "auto", transform: "none" } : undefined}
    >
      <button
        type="button"
        className="app-scroll-controls-drag-handle"
        aria-label="Giữ và kéo để di chuyển thanh cuộn; dùng các phím mũi tên để tinh chỉnh vị trí"
        title="Giữ và kéo để di chuyển"
        onPointerDown={startDragging}
        onPointerMove={drag}
        onPointerUp={stopDragging}
        onPointerCancel={stopDragging}
        onKeyDown={moveWithKeyboard}
      >
        <svg aria-hidden="true" viewBox="0 0 12 24">
          <circle cx="3" cy="5" r="1.2" />
          <circle cx="9" cy="5" r="1.2" />
          <circle cx="3" cy="12" r="1.2" />
          <circle cx="9" cy="12" r="1.2" />
          <circle cx="3" cy="19" r="1.2" />
          <circle cx="9" cy="19" r="1.2" />
        </svg>
      </button>
      {buttons.map(({ direction, amount, disabled }) => (
        <button
          key={direction}
          type="button"
          aria-label={direction === "left" ? "Cuộn sang trái" : "Cuộn sang phải"}
          title={direction === "left" ? "Cuộn sang trái" : "Cuộn sang phải"}
          disabled={disabled}
          onClick={() => scroll(amount)}
        >
          <Arrow direction={direction} />
        </button>
      ))}
    </nav>
  );
}
