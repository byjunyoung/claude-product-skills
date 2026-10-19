/* =============================================================================
 * text-walk.js — every TEXT under a node: characters, absolute position, hidden flag
 *
 * Read-only. Input (a global the caller may prepend, after the CFG line):
 *   ROOT_ID   the frame (or section, or page) to walk. Omitted: the current page.
 * Returns [{ id, text, x, y, hidden }], sorted by y then x. Coordinates are absolute and rounded;
 * hidden is true for a text whose own visibility is off. Blank texts are left out.
 * ========================================================================== */

const g = (n,k)=>{try{return n[k]}catch(e){return undefined}};   // phantom-safe
const collect = async (id) => {
  let root = figma.currentPage;
  if (id) {
    root = await figma.getNodeByIdAsync(id);
    let pg = root; while (pg && pg.type !== "PAGE") pg = g(pg, "parent");
    if (pg) await figma.setCurrentPageAsync(pg);   // the node's own page, so a frame on another page can be read
  }
  const out = [];
  const walk = (n) => { if(!n) return;
    if (n.type==="TEXT") { const ch=g(n,"characters");
      if (ch && ch.trim()) { const b=n.absoluteBoundingBox;
        out.push({ id:n.id, y:b?Math.round(b.y):0, x:b?Math.round(b.x):0, t:ch, h:!n.visible?1:0 }); } }
    const kids=g(n,"children"); if(kids) for(const k of kids) walk(k); };
  walk(root); out.sort((a,b)=> a.y-b.y || a.x-b.x);
  return out.map(o => ({ id:o.id, text:o.t, x:o.x, y:o.y, hidden:!!o.h }));
};
return await collect(typeof ROOT_ID !== "undefined" ? ROOT_ID : null);
