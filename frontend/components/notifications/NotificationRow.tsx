"use client";

import { useRef, useState } from "react";
import type { Notification } from "@/lib/types";
import { Avatar } from "../Avatar";
import { BellIcon, TrashIcon } from "../Icons";
import { RelativeTime } from "../RelativeTime";
import styles from "./NotificationRow.module.css";

type NotificationRowProps = {
  item: Notification;
  onOpen: () => void;
  onDelete: () => void;
};

export function NotificationRow({
  item,
  onOpen,
  onDelete,
}: NotificationRowProps) {
  const [offset, setOffset] = useState(0);

  const start = useRef({ x: 0, y: 0 });
  const mode = useRef<"pending" | "horizontal" | "vertical">("pending");
  const swiped = useRef(false);
  const width = useRef(0);

  return (
    <div className={styles.shell}>
      <button
        type="button"
        className={`${styles.delete} ${styles.left}`}
        onClick={onDelete}
        aria-label="Delete notification"
      >
        <TrashIcon />
        <span>Delete</span>
      </button>

      <button
        type="button"
        className={`${styles.delete} ${styles.right}`}
        onClick={onDelete}
        aria-label="Delete notification"
      >
        <TrashIcon />
        <span>Delete</span>
      </button>

      <article
        className={`${styles.row} ${!item.read ? styles.unread : ""}`}
        style={{ transform: `translateX(${offset}px)` }}
        onPointerDown={(event) => {
          start.current = {
            x: event.clientX,
            y: event.clientY,
          };

          mode.current = "pending";
          swiped.current = false;
          width.current = event.currentTarget.clientWidth;

          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!event.currentTarget.hasPointerCapture(event.pointerId)) {
            return;
          }

          const dx = event.clientX - start.current.x;
          const dy = event.clientY - start.current.y;

          if (
            mode.current === "pending" &&
            Math.max(Math.abs(dx), Math.abs(dy)) > 7
          ) {
            mode.current =
              Math.abs(dx) > Math.abs(dy) + 5
                ? "horizontal"
                : "vertical";
          }

          if (mode.current === "horizontal") {
            swiped.current = true;
            setOffset(Math.max(-110, Math.min(110, dx)));
          }
        }}
        onPointerUp={(event) => {
          if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId);
          }

          const shouldDelete =
            Math.abs(offset) > width.current * 0.4;

          if (shouldDelete) {
            onDelete();
            setOffset(0);
            return;
          }

          setOffset(
            Math.abs(offset) > 55
              ? offset < 0
                ? -92
                : 92
              : 0,
          );
        }}
        onPointerCancel={() => {
          setOffset(0);
          mode.current = "pending";
        }}
        onClick={() => {
          if (swiped.current) {
            swiped.current = false;
            return;
          }

          if (offset !== 0) {
            setOffset(0);
            return;
          }

          onOpen();
        }}
      >
        <span className={styles.event} aria-hidden="true">
          <BellIcon />
        </span>

        {item.actor ? (
          <Avatar user={item.actor} size={40} />
        ) : (
          <Avatar
            name="Jesca Social Work"
            variant="brand"
            size={40}
          />
        )}

        <div className={styles.body}>
          <p className={styles.message}>
            <strong className={styles.actorName}>
              {item.actor?.display_name || "Jesca Social Work"}
            </strong>{" "}
            <span className={styles.notificationText}>
              {item.text}
            </span>
          </p>

          {item.post && (
            <span className={styles.preview}>
              {item.post.preview}
            </span>
          )}

          <small className={styles.time}>
            <RelativeTime value={item.created_at} />
          </small>
        </div>

        {!item.read ? (
          <span
            className={styles.dot}
            role="img"
            aria-label="Unread notification"
          />
        ) : (
          <button
            type="button"
            className={`iconButton ${styles.more}`}
            aria-label="Delete notification"
            onPointerDown={(event) => {
              event.stopPropagation();
            }}
            onClick={(event) => {
              event.stopPropagation();
              onDelete();
            }}
          >
            <TrashIcon />
          </button>
        )}
      </article>
    </div>
  );
}