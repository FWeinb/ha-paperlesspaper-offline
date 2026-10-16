/**
 * Debounced preview requests with at most one in flight. Changes made while a
 * request runs are coalesced: when it returns, only the latest state is sent.
 * (The server renders previews one at a time, so stale requests only add wait.)
 */
export class PreviewQueue {
  private timer?: number;
  /** A change is waiting for its debounce delay. */
  private armed = false;
  private running = false;
  private pending = false;

  /**
   * `run` reads the current draft itself and should drop its result (or error)
   * when `stale()` says a newer draft is waiting. `onBusy` reports whether work
   * is outstanding.
   */
  constructor(
    private readonly run: (stale: () => boolean) => Promise<void>,
    private readonly onBusy: (busy: boolean) => void,
  ) {}

  schedule(delay: number) {
    window.clearTimeout(this.timer);
    this.armed = true;
    this.timer = window.setTimeout(() => {
      this.armed = false;
      void this.fire();
    }, delay);
  }

  cancel() {
    window.clearTimeout(this.timer);
    this.armed = false;
    this.pending = false;
  }

  private async fire() {
    if (this.running) {
      this.pending = true;
      return;
    }
    this.running = true;
    this.onBusy(true);
    try {
      do {
        this.pending = false;
        try {
          await this.run(() => this.pending || this.armed);
        } catch {
          // `run` reports its own errors; keep serving later changes.
        }
      } while (this.pending);
    } finally {
      this.running = false;
      this.onBusy(false);
    }
  }
}
