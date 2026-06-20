/**
 * Script anti-FOUC: corre antes del primer paint y aplica la clase `dark` en
 * <html> según la preferencia guardada (localStorage 'cl-theme') o, en su
 * defecto, la del sistema. Sin esto, el modo oscuro parpadea al cargar.
 */
const THEME_INIT = `(function(){try{var k='cl-theme';var s=localStorage.getItem(k);var m=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;var d=s?s==='dark':m;if(d)document.documentElement.classList.add('dark');}catch(e){}})();`;

export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />;
}
