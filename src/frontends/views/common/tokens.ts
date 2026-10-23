/**
 * Design tokens - phong cách GitHub (Primer)
 * Màu sắc, font chữ, thời gian hiệu ứng
 */

export const colors = {
  fgDefault: '#1f2328',
  fgMuted: '#59636e',
  fgDisabled: '#818b98',
  fgOnEmphasis: '#ffffff',
  fgLink: '#0969da',
  fgAccent: '#0969da',
  fgDanger: '#d1242f',
  fgSuccess: '#1a7f37',
  fgAttention: '#9a6700',
  fgSevere: '#bc4c00',
  fgOpen: '#1a7f37',
  fgClosed: '#d1242f',
  fgDone: '#8250df',

  bgDefault: '#ffffff',
  bgMuted: '#f6f8fa',
  bgInset: '#f6f8fa',
  bgEmphasis: '#25292e',
  bgDangerMuted: '#ffebe9',
  bgSuccessMuted: '#dafbe1',
  bgAttentionMuted: '#fff8c5',
  bgAccentMuted: '#ddf4ff',
  bgDisabled: '#eff2f5',
  bgTransparent: 'transparent',

  btnPrimaryRest: '#1f883d',
  btnPrimaryHover: '#1c8139',
  btnPrimaryActive: '#197935',
  btnPrimaryDisabled: '#95d8a6',
  btnPrimaryFg: '#ffffff',

  btnDefaultRest: '#f6f8fa',
  btnDefaultHover: '#f6f8fa',
  btnDefaultActive: '#e6eaef',
  btnDefaultBorder: '#d1d9e0',
  btnDefaultFg: '#25292e',
  btnDefaultDisabledBg: '#eff2f5',
  btnDefaultDisabledBorder: '#d1d9e0',
  btnDefaultDisabledFg: '#818b98',

  btnDangerRest: '#cf222e',
  btnDangerHover: '#cf222e',
  btnDangerActive: '#a40e26',
  btnDangerFg: '#ffffff',

  btnOutlineRest: 'transparent',
  btnOutlineHover: '#f6f8fa',
  btnOutlineActive: '#e6eaef',
  btnOutlineBorder: '#d1d9e0',
  btnOutlineFg: '#25292e',

  borderDefault: '#d1d9e0',
  borderMuted: 'rgba(129, 139, 152, 0.15)',
  borderEmphasis: '#818b98',

  controlBgRest: '#f6f8fa',
  controlBgHover: '#eff2f5',
  controlBgActive: '#e6eaef',
  controlBgDisabled: '#eff2f5',
  controlBorderRest: '#d1d9e0',
  controlBorderEmphasis: '#818b98',
  controlCheckedBg: '#0969da',
  controlCheckedBorder: '#0969da',
  controlFgRest: '#25292e',
  controlFgPlaceholder: '#59636e',
  controlFgDisabled: '#818b98',

  focusOutline: '#0969da',

  shadowRestingSmall: '0px 1px 1px 0px rgba(31, 35, 40, 0.06), 0px 1px 3px 0px rgba(31, 35, 40, 0.06)',
  shadowRestingMedium: '0px 1px 1px 0px rgba(37, 41, 46, 0.1), 0px 3px 6px 0px rgba(37, 41, 46, 0.12)',
  shadowFloatingSmall: '0px 0px 0px 1px rgba(209, 217, 224, 0.5), 0px 6px 12px -3px rgba(37, 41, 46, 0.04), 0px 6px 18px 0px rgba(37, 41, 46, 0.12)',
}

export const fonts = {
  sansSerif: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji'",
  sansSerifDisplay: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji'",
  monospace: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace",
  system: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji'",
}

export const fontWeights = {
  light: 300,
  normal: 400,
  medium: 500,
  semibold: 600,
}

export const fontSizes = {
  caption: '0.75rem',
  bodySmall: '0.75rem',
  bodyMedium: '0.875rem',
  bodyLarge: '1rem',
  codeBlock: '0.8125rem',
  titleSmall: '1rem',
  titleMedium: '1.25rem',
  titleLarge: '2rem',
  subtitle: '1.25rem',
  display: '2.5rem',
}

export const lineHeights = {
  caption: 1.3333,
  bodySmall: 1.66667,
  bodyMedium: 1.42857,
  bodyLarge: 1.5,
  titleSmall: 1.5,
  titleMedium: 1.6,
  titleLarge: 1.5,
  subtitle: 1.6,
  display: 1.4,
}

export const delayTime = {
  instant: 0,
  fast: 150,
  normal: 200,
  moderate: 300,
  slow: 500,
  fadeIn: 1000,
  pulse: 2000,
}

export const easing = {
  easeIn: 'ease-in',
  easeOut: 'ease-out',
  easeInOut: 'ease-in-out',
  linear: 'linear',
  scaleIn: 'cubic-bezier(0.2, 0, 0.13, 1.5)',
}
