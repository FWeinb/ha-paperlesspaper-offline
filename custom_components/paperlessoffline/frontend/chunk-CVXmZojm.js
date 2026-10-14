var Re = "M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z", Ue = "M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z", Ne = "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z", Oe = "M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z", Te = "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z", ze = "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z", De = "M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z", Ie = "M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z", Be = "M10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,6H12L10,4Z", Ze = "M8.5,13.5L11,16.5L14.5,12L19,18H5M21,19V5C21,3.89 20.1,3 19,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19Z", Fe = "M12.5 21C12.18 20.23 12 19.39 12 18.5C12 18.33 12 18.17 12.03 18H5L8.5 13.5L11 16.5L14.5 12L15.19 12.92C16.16 12.34 17.29 12 18.5 12C19.39 12 20.23 12.18 21 12.5V5C21 4.47 20.79 3.96 20.41 3.59C20.04 3.21 19.53 3 19 3H5C3.9 3 3 3.9 3 5V19C3 19.53 3.21 20.04 3.59 20.41C3.96 20.79 4.47 21 5 21H12.5M17.75 22L15 19L16.16 17.84L17.75 19.43L21.34 15.84L22.5 17.25L17.75 22Z", je = "M22.7 14.3L21.7 15.3L19.7 13.3L20.7 12.3C20.8 12.2 20.9 12.1 21.1 12.1C21.2 12.1 21.4 12.2 21.5 12.3L22.8 13.6C22.9 13.8 22.9 14.1 22.7 14.3M13 19.9V22H15.1L21.2 15.9L19.2 13.9L13 19.9M21 5C21 3.9 20.1 3 19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H11V19.1L12.1 18H5L8.5 13.5L11 16.5L14.5 12L16.1 14.1L21 9.1V5Z", We = "M10,14.29L6.5,19H17.46L14.75,15.46L12.78,17.8L10,14.29M5,21V7H18.96V21H5M12,2.4L14.61,5.03H9.37L12,2.4M5,5.03C4.5,5.03 4,5.22 3.61,5.61C3.2,6 3,6.46 3,7V21C3,21.5 3.2,22 3.61,22.39C4,22.8 4.5,23 5,23H18.96C19.5,23 19.96,22.8 20.37,22.39C20.77,22 21,21.5 21,21V7C21,6.46 20.77,6 20.37,5.61C19.96,5.22 19.5,5.03 18.96,5.03H16L12,1L7.96,5.03H5Z", qe = "M22,16V4A2,2 0 0,0 20,2H8A2,2 0 0,0 6,4V16A2,2 0 0,0 8,18H20A2,2 0 0,0 22,16M11,12L13.03,14.71L16,11L20,16H8M2,6V20A2,2 0 0,0 4,22H18V20H4V6", Ge = "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z", Je = "M13,4.07V1L8.45,5.55L13,10V6.09C15.84,6.57 18,9.03 18,12C18,14.97 15.84,17.43 13,17.91V19.93C16.95,19.44 20,16.08 20,12C20,7.92 16.95,4.56 13,4.07M7.1,18.32C8.26,19.22 9.61,19.76 11,19.93V17.9C10.13,17.75 9.29,17.41 8.54,16.87L7.1,18.32M6.09,13H4.07C4.24,14.39 4.79,15.73 5.69,16.89L7.1,15.47C6.58,14.72 6.23,13.88 6.09,13M7.11,8.53L5.7,7.11C4.8,8.27 4.24,9.61 4.07,11H6.09C6.23,10.13 6.58,9.28 7.11,8.53Z", Ke = "M16.89,15.5L18.31,16.89C19.21,15.73 19.76,14.39 19.93,13H17.91C17.77,13.87 17.43,14.72 16.89,15.5M13,17.9V19.92C14.39,19.75 15.74,19.21 16.9,18.31L15.46,16.87C14.71,17.41 13.87,17.76 13,17.9M19.93,11C19.76,9.61 19.21,8.27 18.31,7.11L16.89,8.53C17.43,9.28 17.77,10.13 17.91,11M15.55,5.55L11,1V4.07C7.06,4.56 4,7.92 4,12C4,16.08 7.05,19.44 11,19.93V17.91C8.16,17.43 6,14.97 6,12C6,9.03 8.16,6.57 11,6.09V10L15.55,5.55Z", Qe = "M16,18H18V6H16M6,18L14.5,12L6,6V18Z", Ye = "M3,17V19H9V17H3M3,5V7H13V5H3M13,21V19H21V17H13V15H11V21H13M7,9V11H3V13H7V15H9V9H7M21,13V11H11V13H21M15,9H17V7H21V5H17V3H15V9Z", Xe = "M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z";
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const E = globalThis, N = E.ShadowRoot && (E.ShadyCSS === void 0 || E.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, O = Symbol(), B = /* @__PURE__ */ new WeakMap();
let ee = class {
  constructor(e, t, r) {
    if (this._$cssResult$ = !0, r !== O) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = t;
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (N && e === void 0) {
      const r = t !== void 0 && t.length === 1;
      r && (e = B.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), r && B.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const oe = (n) => new ee(typeof n == "string" ? n : n + "", void 0, O), ae = (n, ...e) => {
  const t = n.length === 1 ? n[0] : e.reduce((r, i, s) => r + ((o) => {
    if (o._$cssResult$ === !0) return o.cssText;
    if (typeof o == "number") return o;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + o + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(i) + n[s + 1], n[0]);
  return new ee(t, n, O);
}, he = (n, e) => {
  if (N) n.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const r = document.createElement("style"), i = E.litNonce;
    i !== void 0 && r.setAttribute("nonce", i), r.textContent = t.cssText, n.appendChild(r);
  }
}, Z = N ? (n) => n : (n) => n instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const r of e.cssRules) t += r.cssText;
  return oe(t);
})(n) : n;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: le, defineProperty: de, getOwnPropertyDescriptor: ce, getOwnPropertyNames: pe, getOwnPropertySymbols: ue, getPrototypeOf: fe } = Object, P = globalThis, F = P.trustedTypes, ge = F ? F.emptyScript : "", _e = P.reactiveElementPolyfillSupport, C = (n, e) => n, k = { toAttribute(n, e) {
  switch (e) {
    case Boolean:
      n = n ? ge : null;
      break;
    case Object:
    case Array:
      n = n == null ? n : JSON.stringify(n);
  }
  return n;
}, fromAttribute(n, e) {
  let t = n;
  switch (e) {
    case Boolean:
      t = n !== null;
      break;
    case Number:
      t = n === null ? null : Number(n);
      break;
    case Object:
    case Array:
      try {
        t = JSON.parse(n);
      } catch {
        t = null;
      }
  }
  return t;
} }, T = (n, e) => !le(n, e), j = { attribute: !0, type: String, converter: k, reflect: !1, useDefault: !1, hasChanged: T };
Symbol.metadata ??= Symbol("metadata"), P.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
let v = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ??= []).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = j) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const r = Symbol(), i = this.getPropertyDescriptor(e, r, t);
      i !== void 0 && de(this.prototype, e, i);
    }
  }
  static getPropertyDescriptor(e, t, r) {
    const { get: i, set: s } = ce(this.prototype, e) ?? { get() {
      return this[t];
    }, set(o) {
      this[t] = o;
    } };
    return { get: i, set(o) {
      const h = i?.call(this);
      s?.call(this, o), this.requestUpdate(e, h, r);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? j;
  }
  static _$Ei() {
    if (this.hasOwnProperty(C("elementProperties"))) return;
    const e = fe(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(C("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(C("properties"))) {
      const t = this.properties, r = [...pe(t), ...ue(t)];
      for (const i of r) this.createProperty(i, t[i]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [r, i] of t) this.elementProperties.set(r, i);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, r] of this.elementProperties) {
      const i = this._$Eu(t, r);
      i !== void 0 && this._$Eh.set(i, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const r = new Set(e.flat(1 / 0).reverse());
      for (const i of r) t.unshift(Z(i));
    } else e !== void 0 && t.push(Z(e));
    return t;
  }
  static _$Eu(e, t) {
    const r = t.attribute;
    return r === !1 ? void 0 : typeof r == "string" ? r : typeof e == "string" ? e.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
  }
  addController(e) {
    (this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
  }
  removeController(e) {
    this._$EO?.delete(e);
  }
  _$E_() {
    const e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
    for (const r of t.keys()) this.hasOwnProperty(r) && (e.set(r, this[r]), delete this[r]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return he(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    this._$EO?.forEach((e) => e.hostDisconnected?.());
  }
  attributeChangedCallback(e, t, r) {
    this._$AK(e, r);
  }
  _$ET(e, t) {
    const r = this.constructor.elementProperties.get(e), i = this.constructor._$Eu(e, r);
    if (i !== void 0 && r.reflect === !0) {
      const s = (r.converter?.toAttribute !== void 0 ? r.converter : k).toAttribute(t, r.type);
      this._$Em = e, s == null ? this.removeAttribute(i) : this.setAttribute(i, s), this._$Em = null;
    }
  }
  _$AK(e, t) {
    const r = this.constructor, i = r._$Eh.get(e);
    if (i !== void 0 && this._$Em !== i) {
      const s = r.getPropertyOptions(i), o = typeof s.converter == "function" ? { fromAttribute: s.converter } : s.converter?.fromAttribute !== void 0 ? s.converter : k;
      this._$Em = i;
      const h = o.fromAttribute(t, s.type);
      this[i] = h ?? this._$Ej?.get(i) ?? h, this._$Em = null;
    }
  }
  requestUpdate(e, t, r, i = !1, s) {
    if (e !== void 0) {
      const o = this.constructor;
      if (i === !1 && (s = this[e]), r ??= o.getPropertyOptions(e), !((r.hasChanged ?? T)(s, t) || r.useDefault && r.reflect && s === this._$Ej?.get(e) && !this.hasAttribute(o._$Eu(e, r)))) return;
      this.C(e, t, r);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: r, reflect: i, wrapped: s }, o) {
    r && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, o ?? t ?? this[e]), s !== !0 || o !== void 0) || (this._$AL.has(e) || (this.hasUpdated || r || (t = void 0), this._$AL.set(e, t)), i === !0 && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (t) {
      Promise.reject(t);
    }
    const e = this.scheduleUpdate();
    return e != null && await e, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [i, s] of this._$Ep) this[i] = s;
        this._$Ep = void 0;
      }
      const r = this.constructor.elementProperties;
      if (r.size > 0) for (const [i, s] of r) {
        const { wrapped: o } = s, h = this[i];
        o !== !0 || this._$AL.has(i) || h === void 0 || this.C(i, void 0, s, h);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((r) => r.hostUpdate?.()), this.update(t)) : this._$EM();
    } catch (r) {
      throw e = !1, this._$EM(), r;
    }
    e && this._$AE(t);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    this._$EO?.forEach((t) => t.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(e) {
    return !0;
  }
  update(e) {
    this._$Eq &&= this._$Eq.forEach((t) => this._$ET(t, this[t])), this._$EM();
  }
  updated(e) {
  }
  firstUpdated(e) {
  }
};
v.elementStyles = [], v.shadowRootOptions = { mode: "open" }, v[C("elementProperties")] = /* @__PURE__ */ new Map(), v[C("finalized")] = /* @__PURE__ */ new Map(), _e?.({ ReactiveElement: v }), (P.reactiveElementVersions ??= []).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const z = globalThis, W = (n) => n, V = z.trustedTypes, q = V ? V.createPolicy("lit-html", { createHTML: (n) => n }) : void 0, te = "$lit$", g = `lit$${Math.random().toFixed(9).slice(2)}$`, re = "?" + g, me = `<${re}>`, $ = document, L = () => $.createComment(""), H = (n) => n === null || typeof n != "object" && typeof n != "function", D = Array.isArray, $e = (n) => D(n) || typeof n?.[Symbol.iterator] == "function", U = `[ 	
\f\r]`, y = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, G = /-->/g, J = />/g, _ = RegExp(`>|${U}(?:([^\\s"'>=/]+)(${U}*=${U}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), K = /'/g, Q = /"/g, ie = /^(?:script|style|textarea|title)$/i, ne = (n) => (e, ...t) => ({ _$litType$: n, strings: e, values: t }), ve = ne(1), be = ne(2), b = Symbol.for("lit-noChange"), c = Symbol.for("lit-nothing"), Y = /* @__PURE__ */ new WeakMap(), m = $.createTreeWalker($, 129);
function se(n, e) {
  if (!D(n) || !n.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return q !== void 0 ? q.createHTML(e) : e;
}
const Ae = (n, e) => {
  const t = n.length - 1, r = [];
  let i, s = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", o = y;
  for (let h = 0; h < t; h++) {
    const a = n[h];
    let d, p, l = -1, u = 0;
    for (; u < a.length && (o.lastIndex = u, p = o.exec(a), p !== null); ) u = o.lastIndex, o === y ? p[1] === "!--" ? o = G : p[1] !== void 0 ? o = J : p[2] !== void 0 ? (ie.test(p[2]) && (i = RegExp("</" + p[2], "g")), o = _) : p[3] !== void 0 && (o = _) : o === _ ? p[0] === ">" ? (o = i ?? y, l = -1) : p[1] === void 0 ? l = -2 : (l = o.lastIndex - p[2].length, d = p[1], o = p[3] === void 0 ? _ : p[3] === '"' ? Q : K) : o === Q || o === K ? o = _ : o === G || o === J ? o = y : (o = _, i = void 0);
    const f = o === _ && n[h + 1].startsWith("/>") ? " " : "";
    s += o === y ? a + me : l >= 0 ? (r.push(d), a.slice(0, l) + te + a.slice(l) + g + f) : a + g + (l === -2 ? h : f);
  }
  return [se(n, s + (n[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), r];
};
class w {
  constructor({ strings: e, _$litType$: t }, r) {
    let i;
    this.parts = [];
    let s = 0, o = 0;
    const h = e.length - 1, a = this.parts, [d, p] = Ae(e, t);
    if (this.el = w.createElement(d, r), m.currentNode = this.el.content, t === 2 || t === 3) {
      const l = this.el.content.firstChild;
      l.replaceWith(...l.childNodes);
    }
    for (; (i = m.nextNode()) !== null && a.length < h; ) {
      if (i.nodeType === 1) {
        if (i.hasAttributes()) for (const l of i.getAttributeNames()) if (l.endsWith(te)) {
          const u = p[o++], f = i.getAttribute(l).split(g), x = /([.?@])?(.*)/.exec(u);
          a.push({ type: 1, index: s, name: x[2], strings: f, ctor: x[1] === "." ? Ce : x[1] === "?" ? Le : x[1] === "@" ? He : R }), i.removeAttribute(l);
        } else l.startsWith(g) && (a.push({ type: 6, index: s }), i.removeAttribute(l));
        if (ie.test(i.tagName)) {
          const l = i.textContent.split(g), u = l.length - 1;
          if (u > 0) {
            i.textContent = V ? V.emptyScript : "";
            for (let f = 0; f < u; f++) i.append(l[f], L()), m.nextNode(), a.push({ type: 2, index: ++s });
            i.append(l[u], L());
          }
        }
      } else if (i.nodeType === 8) if (i.data === re) a.push({ type: 2, index: s });
      else {
        let l = -1;
        for (; (l = i.data.indexOf(g, l + 1)) !== -1; ) a.push({ type: 7, index: s }), l += g.length - 1;
      }
      s++;
    }
  }
  static createElement(e, t) {
    const r = $.createElement("template");
    return r.innerHTML = e, r;
  }
}
function A(n, e, t = n, r) {
  if (e === b) return e;
  let i = r !== void 0 ? t._$Co?.[r] : t._$Cl;
  const s = H(e) ? void 0 : e._$litDirective$;
  return i?.constructor !== s && (i?._$AO?.(!1), s === void 0 ? i = void 0 : (i = new s(n), i._$AT(n, t, r)), r !== void 0 ? (t._$Co ??= [])[r] = i : t._$Cl = i), i !== void 0 && (e = A(n, i._$AS(n, e.values), i, r)), e;
}
class ye {
  constructor(e, t) {
    this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(e) {
    const { el: { content: t }, parts: r } = this._$AD, i = (e?.creationScope ?? $).importNode(t, !0);
    m.currentNode = i;
    let s = m.nextNode(), o = 0, h = 0, a = r[0];
    for (; a !== void 0; ) {
      if (o === a.index) {
        let d;
        a.type === 2 ? d = new S(s, s.nextSibling, this, e) : a.type === 1 ? d = new a.ctor(s, a.name, a.strings, this, e) : a.type === 6 && (d = new we(s, this, e)), this._$AV.push(d), a = r[++h];
      }
      o !== a?.index && (s = m.nextNode(), o++);
    }
    return m.currentNode = $, i;
  }
  p(e) {
    let t = 0;
    for (const r of this._$AV) r !== void 0 && (r.strings !== void 0 ? (r._$AI(e, r, t), t += r.strings.length - 2) : r._$AI(e[t])), t++;
  }
}
class S {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(e, t, r, i) {
    this.type = 2, this._$AH = c, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = r, this.options = i, this._$Cv = i?.isConnected ?? !0;
  }
  get parentNode() {
    let e = this._$AA.parentNode;
    const t = this._$AM;
    return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(e, t = this) {
    e = A(this, e, t), H(e) ? e === c || e == null || e === "" ? (this._$AH !== c && this._$AR(), this._$AH = c) : e !== this._$AH && e !== b && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : $e(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== c && H(this._$AH) ? this._$AA.nextSibling.data = e : this.T($.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    const { values: t, _$litType$: r } = e, i = typeof r == "number" ? this._$AC(e) : (r.el === void 0 && (r.el = w.createElement(se(r.h, r.h[0]), this.options)), r);
    if (this._$AH?._$AD === i) this._$AH.p(t);
    else {
      const s = new ye(i, this), o = s.u(this.options);
      s.p(t), this.T(o), this._$AH = s;
    }
  }
  _$AC(e) {
    let t = Y.get(e.strings);
    return t === void 0 && Y.set(e.strings, t = new w(e)), t;
  }
  k(e) {
    D(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let r, i = 0;
    for (const s of e) i === t.length ? t.push(r = new S(this.O(L()), this.O(L()), this, this.options)) : r = t[i], r._$AI(s), i++;
    i < t.length && (this._$AR(r && r._$AB.nextSibling, i), t.length = i);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    for (this._$AP?.(!1, !0, t); e !== this._$AB; ) {
      const r = W(e).nextSibling;
      W(e).remove(), e = r;
    }
  }
  setConnected(e) {
    this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
  }
}
class R {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, r, i, s) {
    this.type = 1, this._$AH = c, this._$AN = void 0, this.element = e, this.name = t, this._$AM = i, this.options = s, r.length > 2 || r[0] !== "" || r[1] !== "" ? (this._$AH = Array(r.length - 1).fill(new String()), this.strings = r) : this._$AH = c;
  }
  _$AI(e, t = this, r, i) {
    const s = this.strings;
    let o = !1;
    if (s === void 0) e = A(this, e, t, 0), o = !H(e) || e !== this._$AH && e !== b, o && (this._$AH = e);
    else {
      const h = e;
      let a, d;
      for (e = s[0], a = 0; a < s.length - 1; a++) d = A(this, h[r + a], t, a), d === b && (d = this._$AH[a]), o ||= !H(d) || d !== this._$AH[a], d === c ? e = c : e !== c && (e += (d ?? "") + s[a + 1]), this._$AH[a] = d;
    }
    o && !i && this.j(e);
  }
  j(e) {
    e === c ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class Ce extends R {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === c ? void 0 : e;
  }
}
class Le extends R {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== c);
  }
}
class He extends R {
  constructor(e, t, r, i, s) {
    super(e, t, r, i, s), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = A(this, e, t, 0) ?? c) === b) return;
    const r = this._$AH, i = e === c && r !== c || e.capture !== r.capture || e.once !== r.once || e.passive !== r.passive, s = e !== c && (r === c || i);
    i && this.element.removeEventListener(this.name, this, r), s && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class we {
  constructor(e, t, r) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = r;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    A(this, e);
  }
}
const Se = z.litHtmlPolyfillSupport;
Se?.(w, S), (z.litHtmlVersions ??= []).push("3.3.3");
const xe = (n, e, t) => {
  const r = t?.renderBefore ?? e;
  let i = r._$litPart$;
  if (i === void 0) {
    const s = t?.renderBefore ?? null;
    r._$litPart$ = i = new S(e.insertBefore(L(), s), s, void 0, t ?? {});
  }
  return i._$AI(n), i;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const I = globalThis;
class M extends v {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    const e = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= e.firstChild, e;
  }
  update(e) {
    const t = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = xe(t, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(!0);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(!1);
  }
  render() {
    return b;
  }
}
M._$litElement$ = !0, M.finalized = !0, I.litElementHydrateSupport?.({ LitElement: M });
const Ee = I.litElementPolyfillSupport;
Ee?.({ LitElement: M });
(I.litElementVersions ??= []).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const rt = (n) => (e, t) => {
  t !== void 0 ? t.addInitializer(() => {
    customElements.define(n, e);
  }) : customElements.define(n, e);
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Me = { attribute: !0, type: String, converter: k, reflect: !1, hasChanged: T }, ke = (n = Me, e, t) => {
  const { kind: r, metadata: i } = t;
  let s = globalThis.litPropertyMetadata.get(i);
  if (s === void 0 && globalThis.litPropertyMetadata.set(i, s = /* @__PURE__ */ new Map()), r === "setter" && ((n = Object.create(n)).wrapped = !0), s.set(t.name, n), r === "accessor") {
    const { name: o } = t;
    return { set(h) {
      const a = e.get.call(this);
      e.set.call(this, h), this.requestUpdate(o, a, n, !0, h);
    }, init(h) {
      return h !== void 0 && this.C(o, void 0, n, h), h;
    } };
  }
  if (r === "setter") {
    const { name: o } = t;
    return function(h) {
      const a = this[o];
      e.call(this, h), this.requestUpdate(o, a, n, !0, h);
    };
  }
  throw Error("Unsupported decorator location: " + r);
};
function Ve(n) {
  return (e, t) => typeof t == "object" ? ke(n, e, t) : ((r, i, s) => {
    const o = i.hasOwnProperty(s);
    return i.constructor.createProperty(s, r), o ? Object.getOwnPropertyDescriptor(i, s) : void 0;
  })(n, e, t);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function it(n) {
  return Ve({ ...n, state: !0, attribute: !1 });
}
const X = {
  title: "Photo frames",
  frames: "Frames",
  global_defaults: "Global defaults",
  no_frames: "No frames yet. Add one under Settings → Devices & services.",
  loading: "Loading…",
  tab_photos: "Photos",
  tab_settings: "Settings",
  last_seen: "Last seen",
  never: "never",
  in_sync: "In sync",
  pending: "Waiting for next wake",
  pending_settings: "settings",
  pending_photo: "chosen photo",
  pending_image: "one-off image",
  showing: "Showing",
  up_next: "Up next",
  skip: "Skip",
  placeholder: "Placeholder",
  override: "One-off image",
  wakes_left: "{n} wakes left",
  until_cleared: "until cleared",
  upload: "Upload",
  import: "Import from media",
  drop_here: "Drop photos here to upload",
  uploading: "Uploading {n}…",
  upload_errors: "Some files were skipped:",
  empty_library: "No photos yet. Drop images here, upload, or import from your media.",
  order: "Order",
  order_sequential: "In order",
  order_shuffle: "Shuffle",
  in_rotation: "In rotation",
  not_in_rotation: "Not in rotation",
  custom: "Custom",
  drag_hint: "Drag photos to change the order.",
  edit_photo: "Edit photo",
  name: "Name",
  save: "Save",
  cancel: "Cancel",
  close: "Close",
  delete: "Delete",
  delete_confirm: "Delete “{name}” from this frame?",
  show_next: "Show next",
  copy_to: "Copy to…",
  copied: "Copied to {frame}",
  preview: "Preview on the panel",
  preview_hint: "Dithered exactly as the frame will show it.",
  rendering: "Rendering…",
  crop: "Crop",
  crop_hint: "Drag to crop. Click to set the focal point.",
  lock_aspect: "Match frame shape",
  clear_crop: "Clear crop",
  reset_focal: "Center focal point",
  rotate_left: "Rotate left",
  rotate_right: "Rotate right",
  rendering_settings: "Rendering",
  inherit: "Default",
  inherited_value: "Default: {value}",
  dither: "Dithering",
  serpentine: "Serpentine scanning",
  fit: "Fit",
  background: "Background",
  brightness: "Brightness",
  contrast: "Contrast",
  saturation: "Saturation",
  palette: "Palette",
  on: "On",
  off: "Off",
  dither_floyd_steinberg: "Floyd-Steinberg",
  dither_atkinson: "Atkinson",
  dither_jarvis_judice_ninke: "Jarvis-Judice-Ninke",
  dither_sierra2: "Sierra-2",
  dither_bayer: "Ordered (Bayer)",
  dither_none: "None (nearest colour)",
  fit_cover: "Fill and crop",
  fit_contain: "Fit with borders",
  fit_stretch: "Stretch",
  palette_perceived: "Perceived (as the panel looks)",
  palette_pure: "Pure RGB",
  background_white: "White",
  background_black: "Black",
  frame_settings: "Frame settings",
  mounting: "Mounting",
  mounting_landscape: "Landscape",
  mounting_portrait: "Portrait",
  mounting_landscape_flipped: "Landscape (upside down)",
  mounting_portrait_flipped: "Portrait (upside down)",
  interval: "Refresh interval (minutes)",
  frame_defaults: "Rendering defaults for this frame",
  frame_defaults_hint: "Photos inherit these unless they override them.",
  global_defaults_hint: "Every frame inherits these unless it overrides them.",
  more_options: "Quiet hours, authentication and URLs are in the integration's options.",
  sample_photo: "Sample photo",
  saved: "Saved",
  unsaved: "Unsaved changes",
  error: "Something went wrong: {error}",
  media_root: "Media",
  import_selected: "Import {n}",
  importing: "Importing…",
  no_media: "Nothing here.",
  back: "Back",
  manage: "Manage",
  photos_count: "{enabled} of {total} photos in rotation",
  battery: "Battery {volts} V",
  charging: "charging",
  usb: "USB",
  read_ago: "read {when}",
  overdue: "Hasn't checked in",
  needs_urls: "Needs new URLs, see Repairs"
}, Pe = {
  title: "Bilderrahmen",
  frames: "Rahmen",
  global_defaults: "Globale Standards",
  no_frames: "Noch keine Rahmen. Unter Einstellungen → Geräte & Dienste hinzufügen.",
  loading: "Lädt…",
  tab_photos: "Fotos",
  tab_settings: "Einstellungen",
  last_seen: "Zuletzt gesehen",
  never: "nie",
  in_sync: "Synchron",
  pending: "Wartet auf nächstes Aufwachen",
  pending_settings: "Einstellungen",
  pending_photo: "gewähltes Foto",
  pending_image: "einmaliges Bild",
  showing: "Angezeigt",
  up_next: "Als Nächstes",
  skip: "Überspringen",
  placeholder: "Platzhalter",
  override: "Einmaliges Bild",
  wakes_left: "noch {n}× Aufwachen",
  until_cleared: "bis zum Entfernen",
  upload: "Hochladen",
  import: "Aus Medien importieren",
  drop_here: "Fotos hier ablegen zum Hochladen",
  uploading: "Lade {n} hoch…",
  upload_errors: "Einige Dateien wurden übersprungen:",
  empty_library: "Noch keine Fotos. Bilder hier ablegen, hochladen oder aus den Medien importieren.",
  order: "Reihenfolge",
  order_sequential: "Der Reihe nach",
  order_shuffle: "Zufällig",
  in_rotation: "In der Rotation",
  not_in_rotation: "Nicht in der Rotation",
  custom: "Angepasst",
  drag_hint: "Fotos ziehen, um die Reihenfolge zu ändern.",
  edit_photo: "Foto bearbeiten",
  name: "Name",
  save: "Speichern",
  cancel: "Abbrechen",
  close: "Schließen",
  delete: "Löschen",
  delete_confirm: "„{name}“ aus diesem Rahmen löschen?",
  show_next: "Als Nächstes zeigen",
  copy_to: "Kopieren nach…",
  copied: "Nach {frame} kopiert",
  preview: "Vorschau auf dem Panel",
  preview_hint: "Genau so gedithert, wie der Rahmen es zeigt.",
  rendering: "Wird berechnet…",
  crop: "Ausschnitt",
  crop_hint: "Ziehen zum Zuschneiden. Klicken setzt den Fokuspunkt.",
  lock_aspect: "Rahmenform beibehalten",
  clear_crop: "Ausschnitt entfernen",
  reset_focal: "Fokuspunkt zentrieren",
  rotate_left: "Nach links drehen",
  rotate_right: "Nach rechts drehen",
  rendering_settings: "Darstellung",
  inherit: "Standard",
  inherited_value: "Standard: {value}",
  dither: "Dithering",
  serpentine: "Serpentinen-Abtastung",
  fit: "Einpassung",
  background: "Hintergrund",
  brightness: "Helligkeit",
  contrast: "Kontrast",
  saturation: "Sättigung",
  palette: "Palette",
  on: "An",
  off: "Aus",
  dither_floyd_steinberg: "Floyd-Steinberg",
  dither_atkinson: "Atkinson",
  dither_jarvis_judice_ninke: "Jarvis-Judice-Ninke",
  dither_sierra2: "Sierra-2",
  dither_bayer: "Geordnet (Bayer)",
  dither_none: "Keines (nächste Farbe)",
  fit_cover: "Füllen und zuschneiden",
  fit_contain: "Einpassen mit Rand",
  fit_stretch: "Strecken",
  palette_perceived: "Wahrgenommen (wie das Panel aussieht)",
  palette_pure: "Reines RGB",
  background_white: "Weiß",
  background_black: "Schwarz",
  frame_settings: "Rahmeneinstellungen",
  mounting: "Ausrichtung",
  mounting_landscape: "Querformat",
  mounting_portrait: "Hochformat",
  mounting_landscape_flipped: "Querformat (kopfüber)",
  mounting_portrait_flipped: "Hochformat (kopfüber)",
  interval: "Aktualisierungsintervall (Minuten)",
  frame_defaults: "Darstellungsstandards für diesen Rahmen",
  frame_defaults_hint: "Fotos übernehmen diese, sofern sie sie nicht überschreiben.",
  global_defaults_hint: "Alle Rahmen übernehmen diese, sofern sie sie nicht überschreiben.",
  more_options: "Ruhezeiten, Authentifizierung und URLs sind in den Optionen der Integration.",
  sample_photo: "Beispielfoto",
  saved: "Gespeichert",
  unsaved: "Ungespeicherte Änderungen",
  error: "Etwas ist schiefgelaufen: {error}",
  media_root: "Medien",
  import_selected: "{n} importieren",
  importing: "Importiere…",
  no_media: "Hier ist nichts.",
  back: "Zurück",
  manage: "Verwalten",
  photos_count: "{enabled} von {total} Fotos in der Rotation",
  battery: "Akku {volts} V",
  charging: "lädt",
  usb: "USB",
  read_ago: "gelesen {when}",
  overdue: "Hat sich nicht gemeldet",
  needs_urls: "Braucht neue URLs, siehe Reparaturen"
};
function nt(n) {
  const e = n?.language?.startsWith("de") ? Pe : X;
  return (t, r) => {
    let i = e[t] ?? X[t] ?? t;
    for (const [s, o] of Object.entries(r ?? {}))
      i = i.replace(`{${s}}`, String(o));
    return i;
  };
}
function st(n, e, t) {
  if (!n) return t;
  const r = Math.round((new Date(n).getTime() - Date.now()) / 1e3), i = new Intl.RelativeTimeFormat(e.language || "en", { numeric: "auto" }), s = [
    [60, "second"],
    [60, "minute"],
    [24, "hour"],
    [7, "day"],
    [Number.POSITIVE_INFINITY, "week"]
  ];
  let o = r;
  for (const [h, a] of s) {
    if (Math.abs(o) < h) return i.format(o, a);
    o = Math.round(o / h);
  }
  return i.format(o, "week");
}
const ot = ae`
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
    gap: 4px;
    font-size: 14px;
  }
  .error {
    color: var(--pp-danger);
  }
`, at = (n) => ve`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${be`<path d=${n}></path>`}</svg>`;
export {
  c as A,
  Te as B,
  We as C,
  Oe as D,
  Ge as E,
  M as a,
  ve as b,
  st as c,
  at as d,
  Qe as e,
  Re as f,
  Ne as g,
  Ze as h,
  ae as i,
  Be as j,
  Ue as k,
  nt as l,
  je as m,
  Ve as n,
  Xe as o,
  qe as p,
  Ye as q,
  it as r,
  ot as s,
  rt as t,
  De as u,
  Ie as v,
  Je as w,
  Ke as x,
  ze as y,
  Fe as z
};
