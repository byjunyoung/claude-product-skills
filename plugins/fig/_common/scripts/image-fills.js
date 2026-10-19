/* =============================================================================
 * image-fills.js — nodes that carry an IMAGE fill, for proto's asset list
 *
 * Read-only. Input (a global the caller may prepend, after the CFG line):
 *   ROOT_ID   the frame (or section, or page) to scan. Omitted: the current page.
 * Returns [{ id, name, type, w, h, kids }]; kids > 0 means the node has overlays laid on as
 * children (markers, numbers, badges), which exporting the node whole brings along.
 * ========================================================================== */

const g=(n,k)=>{try{return n[k]}catch(e){return undefined}};
const scan = async (frameId) => {
  let root = figma.currentPage;
  if (frameId) {
    root = await figma.getNodeByIdAsync(frameId);
    let pg = root; while (pg && pg.type !== "PAGE") pg = g(pg, "parent");
    if (pg) await figma.setCurrentPageAsync(pg);   // the node's own page, so a frame on another page can be read
  }
  const hits = [];
  const walk = n => { if(!n) return;
    const fills = g(n,"fills");
    if (Array.isArray(fills) && fills.some(f => f.type === "IMAGE"))
      hits.push({ id:n.id, name:n.name, type:n.type,
                  w:Math.round(n.width), h:Math.round(n.height),
                  kids:(g(n,"children")||[]).length });   // kids>0 = has overlays
    for (const k of (g(n,"children")||[])) walk(k); };
  walk(root); return hits;
};
return await scan(typeof ROOT_ID !== "undefined" ? ROOT_ID : null);
