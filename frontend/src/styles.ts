import { css, html, svg } from "lit";

/** Shared look, built on Home Assistant's theme variables. */
export const sharedStyles = css`
  :host {
    --pp-radius: var(--ha-card-border-radius, 12px);
    --pp-gap: 16px;
    --pp-muted: var(--secondary-text-color, #6b7280);
    --pp-border: var(--divider-color, rgba(0, 0, 0, 0.12));
    --pp-surface: var(--card-background-color, #fff);
    --pp-bg: var(--primary-background-color, #f5f5f5);
    --pp-text: var(--primary-text-color, #1f2937);
    --pp-accent: var(--primary-color, #03a9f4);
    --pp-on-accent: var(--text-primary-color, #fff);
    --pp-warn: var(--warning-color, #f59e0b);
    --pp-ok: var(--success-color, #16a34a);
    --pp-danger: var(--error-color, #dc2626);
    color: var(--pp-text);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, system-ui, sans-serif));
  }
  * {
    box-sizing: border-box;
  }
  button {
    font: inherit;
    cursor: pointer;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 36px;
    padding: 0 14px;
    border-radius: 18px;
    border: 1px solid var(--pp-border);
    background: transparent;
    color: var(--pp-text);
    font-weight: 500;
  }
  .btn:hover {
    background: color-mix(in srgb, var(--pp-text) 6%, transparent);
  }
  .btn.primary {
    background: var(--pp-accent);
    border-color: var(--pp-accent);
    color: var(--pp-on-accent);
  }
  .btn.primary:hover {
    filter: brightness(1.05);
  }
  .btn.danger {
    color: var(--pp-danger);
    border-color: color-mix(in srgb, var(--pp-danger) 40%, transparent);
  }
  .btn[disabled] {
    opacity: 0.5;
    cursor: default;
  }
  .icon-btn {
    display: inline-grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: none;
    background: transparent;
    color: inherit;
  }
  .icon-btn:hover {
    background: color-mix(in srgb, currentColor 10%, transparent);
  }
  svg.icon {
    width: 20px;
    height: 20px;
    fill: currentColor;
    flex: none;
  }
  .card {
    background: var(--pp-surface);
    border-radius: var(--pp-radius);
    border: 1px solid var(--pp-border);
    box-shadow: var(--ha-card-box-shadow, none);
  }
  .muted {
    color: var(--pp-muted);
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    background: color-mix(in srgb, var(--pp-text) 8%, transparent);
  }
  .chip.ok {
    background: color-mix(in srgb, var(--pp-ok) 16%, transparent);
    color: var(--pp-ok);
  }
  .chip.warn {
    background: color-mix(in srgb, var(--pp-warn) 18%, transparent);
    color: color-mix(in srgb, var(--pp-warn) 70%, var(--pp-text));
  }
  select,
  input[type="text"],
  input[type="number"] {
    font: inherit;
    color: var(--pp-text);
    background: var(--pp-surface);
    border: 1px solid var(--pp-border);
    border-radius: 8px;
    min-height: 36px;
    padding: 0 10px;
  }
  input[type="range"] {
    accent-color: var(--pp-accent);
  }
  input[type="checkbox"] {
    accent-color: var(--pp-accent);
    width: 16px;
    height: 16px;
  }
  label.field {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 4px;
    font-size: 14px;
  }
  .error {
    color: var(--pp-danger);
  }
`;

/** Render an @mdi/js path as an inline icon. */
export const icon = (path: string) =>
  html`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${svg`<path d=${path}></path>`}</svg>`;
