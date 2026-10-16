import type { HomeAssistant } from "./types";

const LOAD_TIMEOUT = 3000;
let loading: Promise<boolean> | null = null;

const timeout = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/**
 * Make Home Assistant's own code editor (`ha-code-editor`, as used in
 * Developer tools > Template) available to the panel.
 *
 * HA loads it lazily and custom panels can't import HA internals, so this asks
 * HA's card helpers for the built-in Markdown card editor (which has a template
 * field) and renders it off screen once; that registers `ha-code-editor`.
 * Resolves to false if the editor isn't available (e.g. a future frontend
 * change, or outside HA), so callers can fall back to a plain text field.
 */
export function ensureCodeEditor(hass: HomeAssistant): Promise<boolean> {
  if (customElements.get("ha-code-editor")) return Promise.resolve(true);
  if (!loading) {
    loading = (async () => {
      let host: HTMLElement | null = null;
      try {
        const helpers = await (window as unknown as { loadCardHelpers?: () => Promise<any> })
          .loadCardHelpers?.();
        if (helpers) {
          const card = await helpers.createCardElement({ type: "markdown", content: "" });
          const editor = await card?.constructor?.getConfigElement?.();
          if (editor) {
            editor.hass = hass;
            editor.setConfig?.({ type: "markdown", content: "" });
            host = document.createElement("div");
            host.style.cssText = "position:fixed;left:-10000px;top:0;width:400px;height:300px;overflow:hidden";
            host.setAttribute("aria-hidden", "true");
            host.append(editor);
            document.body.append(host);
          }
        }
        await Promise.race([customElements.whenDefined("ha-code-editor"), timeout(LOAD_TIMEOUT)]);
      } catch {
        // Fall back to the plain text field.
      } finally {
        host?.remove();
      }
      return Boolean(customElements.get("ha-code-editor"));
    })();
  }
  return loading;
}

