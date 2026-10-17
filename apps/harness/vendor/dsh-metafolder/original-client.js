// workspace-groups (wsg): visual meta-folders over the DSH sidebar workspaces.
// Client-only dynamic Cordis plugin. Shadows the `sidebar.workspaces` seat and
// renders the browsing region itself, adding a persisted meta-folder layer over
// real workspace rows. Workspace paths, ordering durability and permissions
// are untouched: assignment to a meta group is display-only, while folder
// reordering uses the real Host workspace order (workspaces.insertBefore).
return {
  apply(ctx) {
    const slots = ctx.get('slots')
    const sessions = ctx.get('sessions')
    const workspaces = ctx.get('workspaces')
    if (slots === undefined || sessions === undefined || workspaces === undefined) {
      console.error('missing sessions/workspaces/slots service')
      return
    }
    const locale = ctx.get('locale')

    const LS_META = 'dsh.wsmeta.v1'
    const LS_SHIPPED = 'dsh.workspace.view.v5'
    // Optional Host persistence. Read through ctx.get so an unmounted
    // namespace returns undefined instead of throwing, and never list
    // 'remote.metafolder' as a required inject: no package mounts that
    // namespace in this DSH build, and requiring it hung the web boot.
    const META_REMOTE = ctx.get('remote.metafolder')
    const LIMIT5 = 5
    const SEARCH_MS = 250
    // Curated meta-folder colours: mid-tone hues that stay legible on both the
    // light and the dark DSH theme.
    const META_COLORS = ['#e5484d', '#f76b15', '#ffb224', '#46a758', '#12a594', '#0091ff', '#8e4ec6', '#e93d82']

    // ---------- own labels (the `workspace` ns stays the shipped one) ----------
    const DICT = {
      en: {
        newGroup: 'New meta folder', create: 'Create', folderName: 'Meta folder name',
        addGroup: 'New meta folder', groupActions: 'Meta folder “{name}” actions',
        renameGroup: 'Rename meta folder', deleteGroup: 'Delete meta folder',
        moveUp: 'Move up', moveDown: 'Move down',
        ungroup: 'Remove from meta folder', ungroupedHint: 'No meta folder',
        deleteGroupDesc: 'The meta folder is removed. The workspace folders stay in place and return to the main list.',
        emptyGroup: 'empty',
        dndHint: 'Drag a workspace folder onto a meta folder to file it — drop it here to take it out.',
        dndNoMeta: 'No meta folder yet — create one with the folder + button, then drag workspaces into it.',
        colorLabel: 'Colour', colorAria: 'Use colour {color}', colorDefault: 'Theme colour', colorCustom: 'Custom colour',
        newWorkspaceHere: 'New workspace in this meta folder',
        newWorkspaceTitle: 'New workspace',
        newWorkspaceInTitle: 'New workspace in “{name}”',
        newWorkspaceHint: 'The folder must already exist on the host. The new workspace opens a session and is filed into the meta folder.',
        workspacePath: 'Workspace folder path',
        workspacePathPlaceholder: '/home/you/projects/my-project',
        browse: 'Browse…', home: 'Home', parentFolder: 'Up one folder',
        folderList: 'Folders', emptyDirectory: 'No subfolders', showHidden: 'Show hidden folders',
        truncatedFolders: 'Some folders are omitted. Enter their full path above.',
        pickerUnavailable: 'No directory picker is available in this composition.',
      },
      zh: {
        newGroup: '新建分组', create: '创建', folderName: '分组名称',
        addGroup: '新建分组文件夹', groupActions: '分组“{name}”的操作',
        renameGroup: '重命名分组', deleteGroup: '删除分组',
        moveUp: '上移', moveDown: '下移',
        ungroup: '移出分组', ungroupedHint: '未分组',
        deleteGroupDesc: '将移除该分组文件夹。工作区文件夹保持原位并回到主列表。',
        emptyGroup: '空',
        dndHint: '把工作区文件夹拖到分组文件夹即可归类；拖到此处可移出。',
        dndNoMeta: '还没有分组文件夹——先用文件夹 + 按钮创建，再拖入工作区。',
        colorLabel: '颜色', colorAria: '使用颜色 {color}', colorDefault: '主题色', colorCustom: '自定义颜色',
        newWorkspaceHere: '在此分组中新建工作区',
        newWorkspaceTitle: '新建工作区',
        newWorkspaceInTitle: '在“{name}”中新建工作区',
        newWorkspaceHint: '该文件夹必须已存在。新工作区会打开一个会话并归入该分组。',
        workspacePath: '工作区文件夹路径',
        workspacePathPlaceholder: '/home/you/projects/my-project',
        browse: '浏览…', home: '主目录', parentFolder: '上一级',
        folderList: '文件夹', emptyDirectory: '没有子文件夹', showHidden: '显示隐藏文件夹',
        truncatedFolders: '部分文件夹未显示。请在上方输入完整路径。',
        pickerUnavailable: '当前组合中没有可用的目录选择器。',
      },
    }
    let lang = 'en'
    try {
      if (locale !== undefined && locale.getLocale !== undefined) {
        const id = String((locale.getLocale() || {}).id || 'en')
        if (id.toLowerCase().indexOf('zh') === 0) lang = 'zh'
      }
    } catch (e) { /* keep en */ }
    function tm(key, params) {
      const table = DICT[lang] !== undefined ? DICT[lang] : DICT.en
      let s = table[key] !== undefined ? table[key] : (DICT.en[key] !== undefined ? DICT.en[key] : key)
      if (params !== undefined) s = s.replace(/\{(\w+)\}/g, (m, p) => (params[p] !== undefined ? String(params[p]) : m))
      return s
    }

    // ---------- persistence (localStorage; same mechanism the shipped store uses) ----------
    function blankDoc() { return { v: 2, groups: [], assignment: {}, sessionAssignment: {}, metaCollapsed: {}, expanded: {}, groupBy: 'workspace', orderBy: 'manual' } }
    function asObj(x) { return x !== null && typeof x === 'object' ? x : {} }
    function readDoc() {
      try {
        const raw = JSON.parse(localStorage.getItem(LS_META))
        if (raw !== null && typeof raw === 'object' && Array.isArray(raw.groups)) {
          return {
            v: 2,
            groups: raw.groups
              .filter((g) => g !== null && typeof g === 'object' && typeof g.id === 'string' && typeof g.name === 'string')
              .map((g) => ({
                id: g.id, name: g.name,
                color: typeof g.color === 'string' && /^#[0-9a-fA-F]{3,8}$/.test(g.color) ? g.color : undefined,
              })),
            assignment: asObj(raw.assignment), sessionAssignment: asObj(raw.sessionAssignment), metaCollapsed: asObj(raw.metaCollapsed), expanded: asObj(raw.expanded),
            groupBy: raw.groupBy === 'flat' ? 'flat' : 'workspace',
            orderBy: raw.orderBy === 'updated' ? 'updated' : 'manual',
          }
        }
      } catch (e) { /* fall through */ }
      return blankDoc()
    }
    function saveDoc(doc) {
      try { localStorage.setItem(LS_META, JSON.stringify(doc)) } catch (e) { /* quota */ }
      // Host persistence is authoritative when the optional service is mounted.
      // The local copy remains a compatibility cache for older DSH compositions.
      try {
        if (META_REMOTE !== undefined && typeof META_REMOTE.save === 'function') {
          Promise.resolve(META_REMOTE.save(doc)).catch((e) => console.warn('metafolder persistence failed', e))
        }
      } catch (e) { /* optional host service */ }
    }
    async function loadDoc() {
      try {
        if (META_REMOTE !== undefined && typeof META_REMOTE.load === 'function') {
          const result = await META_REMOTE.load()
          if (result !== undefined && result !== null && typeof result === 'object' && Array.isArray(result.groups)) return result
        }
      } catch (e) { console.warn('metafolder load failed', e) }
      return readDoc()
    }
    // Read-only borrow of the shipped view store so existing manual session order carries over.
    let sv = {}
    try {
      sv = asObj(JSON.parse(localStorage.getItem(LS_SHIPPED)))
      if (sv.orderBy === undefined && asObj(sv.state).groupBy !== undefined) sv = asObj(sv.state)
    } catch (e) { /* defaults */ }
    // Read-only borrow of the shipped view store: the shipped manual session
    // order (and the flat account it keeps) is honoured by our "Manual" mode,
    // so the ordering users already arranged is not lost when we take the seat.
    const shippedAccounts = asObj(sv.sessionOrderByAccount)

    // ---------- styles ----------
    const css = [
      '.wsg-root{display:flex;flex-direction:column;flex:1;min-height:0;color:var(--dsw-alias-label-primary);}',
      '.wsg-head{display:flex;align-items:center;gap:4px;padding:6px 8px;flex:0 0 auto;}',
      '.wsg-head-rail{flex-direction:column;align-items:center;gap:2px;padding:8px 0;}',
      '.wsg-title{flex:1;font-size:12px;color:var(--dsw-alias-label-secondary);}',
      '.wsg-list{flex:1;min-height:0;overflow-y:auto;padding:0 6px 16px;}',
      '.wsg-list.wsg-list-drop{box-shadow:inset 0 0 0 2px color-mix(in srgb, var(--dsw-alias-brand-primary) 55%, transparent);border-radius:8px;}',
      '.wsg-hint{margin:0 8px 6px;font-size:11px;line-height:15px;color:var(--dsw-alias-label-secondary);}',
      '.wsg-row.wsg-dragging{opacity:.45;cursor:grabbing;}',
      '.wsg-ghost{position:fixed;left:0;top:0;z-index:9999;pointer-events:none;padding:4px 9px;border-radius:6px;background:var(--dsw-alias-bg-overlay);border:1px solid var(--dsw-alias-border-l1);box-shadow:0 10px 26px rgba(0,0,0,.28);font-size:12px;color:var(--dsw-alias-label-primary);max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}',
      '.wsg-drop{outline:2px dashed var(--wsg-accent);outline-offset:-3px;border-radius:8px;background:color-mix(in srgb, var(--wsg-accent) 10%, transparent);}',
      '.wsg-drop-hint{outline:2px dashed color-mix(in srgb, var(--wsg-accent) 45%, transparent);outline-offset:-3px;border-radius:8px;}',
      '.wsg-row.wsg-over{background:var(--dsw-alias-bg-layer-2);}',
      '.wsg-row{display:flex;align-items:center;gap:6px;height:30px;padding:0 6px;border-radius:6px;cursor:pointer;user-select:none;position:relative;font-size:13px;}',
      '.wsg-row:hover{background:var(--dsw-alias-bg-layer-1);}',
      '.wsg-row.wsg-sel{background:var(--dsw-alias-bg-layer-2);}',
      '.wsg-row.wsg-active .wsg-glyph{color:var(--dsw-alias-brand-primary);}',
      '.wsg-glyph{width:16px;flex:0 0 16px;display:inline-flex;align-items:center;justify-content:center;color:var(--dsw-alias-label-secondary);}',
      '.wsg-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}',
      '.wsg-time{flex:0 0 auto;font-size:11px;color:var(--dsw-alias-label-secondary);}',
      '.wsg-count{font-size:11px;color:var(--dsw-alias-label-secondary);}',
      '.wsg-dot{width:6px;height:6px;border-radius:50%;display:inline-block;}',
      '.wsg-dot-running{background:var(--dsw-alias-brand-primary);animation:wsg-pulse 1.6s ease-in-out infinite;}',
      '.wsg-dot-warn{background:var(--dsw-alias-state-warn-primary);}',
      '.wsg-dot-done{background:var(--dsw-alias-state-success-primary);}',
      '@keyframes wsg-pulse{50%{opacity:.3}}',
      '.wsg-acts{flex:0 0 auto;display:inline-flex;gap:2px;opacity:0;pointer-events:none;}',
      '.wsg-row:hover .wsg-acts,.wsg-row:focus-within .wsg-acts,.wsg-row.wsg-open .wsg-acts{opacity:1;pointer-events:auto;}',
      '.wsg-btn{border:0;background:transparent;color:var(--dsw-alias-label-secondary);min-width:22px;height:22px;padding:0 2px;border-radius:5px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;}',
      '.wsg-btn:hover{background:var(--dsw-alias-bg-layer-2);color:var(--dsw-alias-label-primary);}',
      '.wsg-newgroup{color:var(--dsw-alias-brand-primary);}',
      '.wsg-newgroup:hover{background:var(--dsw-alias-bg-layer-2);color:var(--dsw-alias-brand-primary);}',
      '.wsg-menu-wrap{position:relative;display:inline-flex;}',
      '.wsg-menu{position:absolute;right:0;top:24px;z-index:60;min-width:180px;max-height:320px;overflow-y:auto;background:var(--dsw-alias-bg-overlay);border:1px solid var(--dsw-alias-border-l1);border-radius:8px;padding:4px;box-shadow:0 10px 28px rgba(0,0,0,.22);}',
      '.wsg-mitem{display:block;width:100%;text-align:left;border:0;background:transparent;color:var(--dsw-alias-label-primary);font-size:13px;padding:6px 8px;border-radius:6px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
      '.wsg-mitem:hover{background:var(--dsw-alias-bg-layer-2);}',
      '.wsg-mdanger{color:var(--dsw-alias-state-error-primary);}',
      '.wsg-msep{height:1px;background:var(--dsw-alias-border-l1);margin:4px 6px;}',
      '.wsg-mhead{font-size:11px;color:var(--dsw-alias-label-secondary);padding:5px 8px 2px;}',
      '.wsg-more{margin:2px 0 6px;color:var(--dsw-alias-label-secondary);font-size:12px;padding:4px 8px;cursor:pointer;border:0;background:transparent;border-radius:6px;}',
      '.wsg-more:hover{background:var(--dsw-alias-bg-layer-1);color:var(--dsw-alias-label-primary);}',
      '.wsg-empty{padding:10px 8px;font-size:12px;color:var(--dsw-alias-label-secondary);}',
      '.wsg-searchbox{flex:1;display:flex;align-items:center;gap:4px;background:var(--dsw-alias-bg-layer-1);border-radius:6px;padding:0 6px;height:26px;min-width:0;}',
      '.wsg-searchbox input{flex:1;min-width:0;border:0;outline:none;background:transparent;color:var(--dsw-alias-label-primary);font-size:13px;}',
      '.wsg-scrim{position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:90;display:flex;align-items:center;justify-content:center;}',
      '.wsg-modal{width:min(380px,92vw);background:var(--dsw-alias-bg-layer-1);border:1px solid var(--dsw-alias-border-l1);border-radius:12px;padding:16px;box-shadow:0 16px 48px rgba(0,0,0,.3);}',
      '.wsg-mtitle{font-size:14px;font-weight:600;}',
      '.wsg-mdesc{margin-top:8px;font-size:12px;color:var(--dsw-alias-label-secondary);}',
      '.wsg-input{width:100%;box-sizing:border-box;margin-top:12px;padding:6px 8px;border-radius:8px;border:1px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-base);color:var(--dsw-alias-label-primary);font-size:13px;outline:none;}',
      '.wsg-merr{margin-top:8px;font-size:12px;color:var(--dsw-alias-state-error-primary);}',
      '.wsg-pathrow{display:flex;align-items:center;gap:8px;margin-top:12px;}',
      '.wsg-pathrow .wsg-input{margin-top:0;flex:1;min-width:0;}',
      '.wsg-pathrow .wsg-obtn{flex:0 0 auto;white-space:nowrap;}',
      '.wsg-colors{display:flex;align-items:center;gap:6px;margin-top:12px;flex-wrap:wrap;}',
      '.wsg-colorlabel{font-size:12px;color:var(--dsw-alias-label-secondary);margin-right:2px;}',
      '.wsg-swatch{width:20px;height:20px;border-radius:50%;border:1px solid var(--dsw-alias-border-l2);padding:0;cursor:pointer;}',
      '.wsg-swatch.wsg-swatch-on{outline:2px solid var(--dsw-alias-label-primary);outline-offset:1px;}',
      '.wsg-swatch-def{background:var(--dsw-alias-label-primary);}',
      '.wsg-colorinput{width:28px;height:22px;padding:0;border:1px solid var(--dsw-alias-border-l2);border-radius:6px;background:transparent;cursor:pointer;}',
      '.wsg-foot{display:flex;justify-content:flex-end;gap:8px;margin-top:14px;}',
      '.wsg-obtn,.wsg-pbtn{border-radius:8px;padding:5px 12px;font-size:13px;cursor:pointer;border:1px solid var(--dsw-alias-border-l1);background:transparent;color:var(--dsw-alias-label-primary);}',
      '.wsg-pbtn{background:var(--dsw-alias-brand-primary);border-color:transparent;color:#fff;}',
      '.wsg-obtn:disabled,.wsg-pbtn:disabled{opacity:.5;cursor:default;}',
      '.wsg-pbtn.wsg-dangerbtn{background:var(--dsw-alias-state-error-primary);}',
      '.wsg-result{display:flex;flex-direction:column;gap:2px;min-height:44px;justify-content:center;padding:4px 8px;border:0;width:100%;text-align:left;background:transparent;border-radius:6px;cursor:pointer;color:inherit;}',
      '.wsg-result:hover{background:var(--dsw-alias-bg-layer-1);}',
      '.wsg-result.wsg-sel{background:var(--dsw-alias-bg-layer-2);}',
      '.wsg-rhead{display:flex;align-items:center;gap:6px;font-size:13px;min-width:0;}',
      '.wsg-rmeta{font-size:11px;color:var(--dsw-alias-label-secondary);display:flex;gap:8px;min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;}',
      '.wsg-err{margin:0 8px 6px;padding:6px 8px;border-radius:6px;font-size:12px;color:var(--dsw-alias-state-error-primary);background:var(--dsw-alias-bg-layer-1);}',
    ].join('\n')
    if (typeof styles !== 'undefined' && styles.insert !== undefined) {
      ctx.effect(() => styles.insert(css), 'wsg:css')
    } else if (typeof document !== 'undefined' && document.querySelector('style[data-plugin-css="dsh-workspace-groups/styles.css"]') === null) {
      // Packaged client half: the dynamic runtime's `styles` service is absent,
      // so own the stylesheet tag instead (idempotent across mounts).
      const tag = document.createElement('style')
      tag.dataset.pluginCss = 'dsh-workspace-groups/styles.css'
      tag.textContent = css
      document.head.appendChild(tag)
    }

    // ---------- element/icon helpers ----------
    const h = React.createElement
    const useState = React.useState
    const useEffect = React.useEffect

    function svg(d, size) {
      return h('svg', { width: size, height: size, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' }, h('path', { d }))
    }
    const icoFolder = (s) => svg('M1.8 4.3c0-.7.5-1.3 1.2-1.3h2.4l1.6 1.8h6.1c.7 0 1.2.5 1.2 1.2v6.5c0 .7-.5 1.3-1.2 1.3H3c-.7 0-1.2-.6-1.2-1.3z', s)
    const icoGroup = (s) => svg('M1.8 6.5c0-.7.5-1.3 1.2-1.3h2.9l1.5 1.5h6.8c.7 0 1.2.5 1.2 1.2v4.6c0 .7-.5 1.3-1.2 1.3H3c-.7 0-1.2-.6-1.2-1.3zM1.8 3.8h4.4l1.1 1.4', s)
    // The shipped "Add workspace…" glyph (IconProjectAddOutline16), reproduced
    // exactly so the toolbar keeps the icon users already know.
    const icoProjectAdd = (s) => h('svg', { width: s, height: s, viewBox: '0 0 16 16', fill: 'none', 'aria-hidden': 'true' },
      h('path', { transform: 'translate(9.52 2.52)', fill: 'currentColor', d: 'M3.55246 0L3.55246 2.44252L6 2.44252L6 3.55748L3.55246 3.55748L3.55246 6L2.43834 6L2.43834 3.55748L0 3.55748L0 2.44252L2.43834 2.44252L2.43834 0L3.55246 0Z' }),
      h('path', { transform: 'translate(0.3496 2.35)', fill: 'currentColor', d: 'M4.76367 0C5.36861 1.80598e-05 5.93113 0.310294 6.25488 0.821289L6.78027 1.64941C6.79685 1.67558 6.81791 1.69775 6.83887 1.71973C6.72186 2.15521 6.65702 2.61192 6.65137 3.08301C6.25601 2.96045 5.90909 2.70478 5.68164 2.3457L5.15723 1.5166C5.07183 1.38189 4.92318 1.3008 4.76367 1.30078L2.32422 1.30078C1.7589 1.30078 1.30078 1.7589 1.30078 2.32422L1.30078 10.1338C1.30078 10.6991 1.7589 11.1572 2.32422 11.1572L11.9766 11.1572C12.5419 11.1572 13 10.6991 13 10.1338L13 8.58398C13.4545 8.5135 13.8903 8.38748 14.3008 8.21289L14.3008 10.1338C14.3008 11.4171 13.2598 12.458 11.9766 12.458L2.32422 12.458C1.04093 12.458 0 11.4171 0 10.1338L0 2.32422C0 1.04093 1.04093 0 2.32422 0L4.76367 0Z' }))

    // Distinct "new meta folder" glyph: folder outline with a plus inside.
    const icoFolderPlus = (s) => h('svg', { width: s, height: s, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' },
      h('path', { d: 'M1.8 4.3c0-.7.5-1.3 1.2-1.3h2.4l1.6 1.8h6.1c.7 0 1.2.5 1.2 1.2v6.5c0 .7-.5 1.3-1.2 1.3H3c-.7 0-1.2-.6-1.2-1.3z' }),
      h('path', { d: 'M8 7.5v3.4M6.3 9.2h3.4' }))
    const icoPlus = (s) => svg('M8 3.3v9.4M3.3 8h9.4', s)
    const icoSearch = (s) => svg('M10.8 10.8 13.9 13.9M11.9 7.2a4.7 4.7 0 1 1-9.4 0 4.7 4.7 0 0 1 9.4 0z', s)
    const icoClose = (s) => svg('M4.2 4.2 11.8 11.8M11.8 4.2 4.2 11.8', s)
    // View options (group by / order by) trigger: two rails with knobs.
    const icoSliders = (s) => h('svg', { width: s, height: s, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.4, 'stroke-linecap': 'round', 'aria-hidden': 'true' },
      h('path', { d: 'M2.5 4.5h11M2.5 11.5h11' }),
      h('circle', { cx: 6, cy: 4.5, r: 1.7, fill: 'var(--dsw-alias-bg-overlay)' }),
      h('circle', { cx: 10.5, cy: 11.5, r: 1.7, fill: 'var(--dsw-alias-bg-overlay)' }))
    function icoChevron(open) {
      return h('svg', { width: 10, height: 10, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', style: { transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .12s' } }, h('path', { d: 'M6 3.5 10.5 8 6 12.5' }))
    }
    function icoDots(s) {
      return h('svg', { width: s, height: s, viewBox: '0 0 16 16', fill: 'currentColor', 'aria-hidden': 'true' },
        h('circle', { cx: 3.2, cy: 8, r: 1.25 }), h('circle', { cx: 8, cy: 8, r: 1.25 }), h('circle', { cx: 12.8, cy: 8, r: 1.25 }))
    }

    // ---------- pure helpers ----------
    function workspaceLabel(cwd) {
      if (cwd === undefined || cwd === '') return tm('ungroupedHint')
      const base = cwd.replace(/[/\\]+$/, '').split(/[/\\]/).pop()
      return base !== undefined && base !== '' ? base : cwd
    }
    function byRecency(a, b) {
      if (b.updatedAt !== a.updatedAt) return b.updatedAt - a.updatedAt
      return a.id < b.id ? -1 : 1
    }
    function relativeTime(updatedAt, now) {
      const MIN = 6e4; const HOUR = 36e5; const DAY = 864e5
      const diff = Math.max(0, now - updatedAt)
      if (diff < MIN) return { unit: 'now', n: 0 }
      if (diff < HOUR) return { unit: 'minutes', n: Math.floor(diff / MIN) }
      if (diff < DAY) return { unit: 'hours', n: Math.floor(diff / HOUR) }
      if (diff < 30 * DAY) return { unit: 'days', n: Math.floor(diff / DAY) }
      if (diff < 365 * DAY) return { unit: 'months', n: Math.floor(diff / (30 * DAY)) }
      return { unit: 'years', n: Math.floor(diff / (365 * DAY)) }
    }
    function timeLabel(updatedAt, now, t) {
      const r = relativeTime(updatedAt, now)
      return r.unit === 'now' ? t('time.now') : t('time.' + r.unit, { n: r.n })
    }
    function sanitize(q) {
      const s = String(q || '').replace(/\u0000/g, '')
      if (s.length <= 500) return s
      let cut = 500
      const code = s.charCodeAt(cut - 1)
      if (code >= 0xD800 && code <= 0xDBFF) cut -= 1
      return s.slice(0, cut)
    }
    function statusView(node, t) {
      if (node.pendingInteraction === 'approval') return { state: 'warn', label: t('status.waitingApproval') }
      if (node.pendingInteraction === 'plan-review') return { state: 'warn', label: t('status.planReview') }
      if (node.pendingInteraction === 'question') return { state: 'warn', label: t('status.waitingAnswer') }
      if (node.running === true) return { state: 'running', label: t('status.running') }
      if (node.subCount > 0) return { state: 'running', label: t(node.subCount === 1 ? 'status.subagentsRunning.one' : 'status.subagentsRunning.other', { n: node.subCount }) }
      if (node.completed === true) return { state: 'done', label: t('status.completed') }
      return undefined
    }

    // Start (reuse-or-create) the blank Session of one Workspace and open it.
    // Mirror of the shipped browser's connectWorkspace/openWorkspace, driven by
    // the pure Client services instead of the shipped uiWorkspace service.
    function openReal(sessionId) {
      sessions.open(sessionId)
      try {
        const layout = ctx.get('layout')
        if (layout !== undefined && typeof layout.selectPanel === 'function') layout.selectPanel(null)
      } catch (e) { /* the main panel stays where it is */ }
    }
    function startSessionIn(workspaceId) {
      try {
        const snap = workspaces.list.getSnapshot()
        const ws = snap.items.filter((it) => it.workspaceId === workspaceId)[0]
        const list = sessions.list.getSnapshot()
        const archived = new Set(Array.from(snap.archivedSessionIds || []))
        if (ws !== undefined) {
          for (const id of list.ids) {
            const s = list.byId[id]
            if (s !== undefined && s.blank === true && s.cwd === ws.path && ws.sessionIds.indexOf(id) !== -1 && !archived.has(id)) { openReal(id); return }
          }
        }
        Promise.resolve(sessions.create({ workspaceId })).then((id) => openReal(id), (r) => console.error('new session failed', r))
      } catch (e) { console.error('new session failed', e) }
    }

    // ---------- stable subcomponents (defined once per apply) ----------
    function Menu(props) {
      const [open, setOpen] = useState(false)
      const root = React.useRef(null)
      useEffect(() => {
        if (!open) return undefined
        const onDoc = (e) => { if (root.current !== null && !root.current.contains(e.target)) setOpen(false) }
        const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
        document.addEventListener('mousedown', onDoc, true)
        document.addEventListener('keydown', onKey)
        return () => { document.removeEventListener('mousedown', onDoc, true); document.removeEventListener('keydown', onKey) }
      }, [open])
      useEffect(() => { props.onOpenChange(open) }, [open])
      return h('span', { className: 'wsg-menu-wrap', ref: root },
        h('button', { type: 'button', className: 'wsg-btn', 'aria-label': props.label, title: props.label, onClick: (e) => { e.stopPropagation(); setOpen((v) => !v) } }, props.icon !== undefined ? props.icon : icoDots(15)),
        open ? h('div', { className: 'wsg-menu', role: 'menu' }, props.items.map((it, i) => {
          if (it.sep === true) return h('div', { className: 'wsg-msep', key: 'sep' + i })
          if (it.header === true) return h('div', { className: 'wsg-mhead', key: 'h' + i }, it.label)
          return h('button', {
            type: 'button', role: 'menuitem', key: (it.id || 'i') + i,
            className: 'wsg-mitem' + (it.danger === true ? ' wsg-mdanger' : ''),
            onMouseDown: (e) => { e.stopPropagation(); e.preventDefault(); setOpen(false); it.run() },
          }, it.label)
        })) : null)
    }

    function Modal(props) {
      useEffect(() => {
        if (!props.open) return undefined
        const onKey = (e) => { if (e.key === 'Escape') props.onClose() }
        document.addEventListener('keydown', onKey)
        return () => document.removeEventListener('keydown', onKey)
      }, [props.open])
      if (!props.open) return null
      let cancelLabel = 'Cancel'
      try { const v = props.t('cancel'); if (typeof v === 'string' && v !== 'cancel') cancelLabel = v } catch (e) { /* keep */ }
      return h('div', { className: 'wsg-scrim', onMouseDown: () => props.onClose() },
        h('div', { className: 'wsg-modal', role: 'dialog', 'aria-modal': 'true', 'aria-label': props.title, onMouseDown: (e) => e.stopPropagation() },
          h('div', { className: 'wsg-mtitle' }, props.title),
          props.desc !== undefined ? h('div', { className: 'wsg-mdesc' }, props.desc) : null,
          props.children,
          h('div', { className: 'wsg-foot' },
            h('button', { type: 'button', className: 'wsg-obtn', onClick: props.onClose }, cancelLabel),
            h('button', { type: 'button', className: 'wsg-pbtn' + (props.danger === true ? ' wsg-dangerbtn' : ''), disabled: props.disabled === true, onClick: props.onConfirm }, props.confirmLabel))))
    }

    function NameModal(props) {
      const [value, setValue] = useState(props.initial)
      const [busy, setBusy] = useState(false)
      const [err, setErr] = useState(null)
      // Meta-folder colour: undefined keeps the theme's normal label colour.
      const [color, setColor] = useState(props.color)
      function confirm() {
        const trimmed = value.trim()
        if (trimmed === '' || busy) return
        setBusy(true); setErr(null)
        Promise.resolve(props.onConfirm(trimmed, color)).then(() => { setBusy(false) }, (reason) => {
          setBusy(false)
          setErr(reason instanceof Error ? reason.message : String(reason))
        })
      }
      return h(Modal, {
        open: true, t: props.t, title: props.title, confirmLabel: props.confirmLabel !== undefined ? props.confirmLabel : tm('create'),
        disabled: busy || value.trim() === '', onClose: props.onClose, onConfirm: confirm,
      },
        h('input', {
          className: 'wsg-input', value, autoFocus: true, 'aria-label': props.fieldLabel !== undefined ? props.fieldLabel : tm('folderName'),
          onFocus: (e) => { try { e.target.select() } catch (e2) { /* noop */ } },
          disabled: busy,
          onChange: (e) => setValue(e.target.value),
          onKeyDown: (e) => { if (e.key === 'Enter') { e.preventDefault(); confirm() } },
        }),
        props.withColor === true ? h('div', { className: 'wsg-colors', role: 'group', 'aria-label': tm('colorLabel') },
          h('span', { className: 'wsg-colorlabel' }, tm('colorLabel')),
          META_COLORS.map((c) => h('button', {
            key: c, type: 'button', className: 'wsg-swatch' + (color === c ? ' wsg-swatch-on' : ''),
            style: { background: c }, title: c, 'aria-label': tm('colorAria', { color: c }),
            onClick: () => setColor(c),
          })),
          h('button', {
            type: 'button', className: 'wsg-swatch wsg-swatch-def' + (color === undefined ? ' wsg-swatch-on' : ''),
            title: tm('colorDefault'), 'aria-label': tm('colorDefault'),
            onClick: () => setColor(undefined),
          }),
          h('input', {
            type: 'color', className: 'wsg-colorinput', 'aria-label': tm('colorCustom'),
            value: typeof color === 'string' && /^#[0-9a-fA-F]{6}$/.test(color) ? color : '#0091ff',
            onChange: (e) => setColor(e.target.value),
          })) : null,
        err !== null ? h('div', { className: 'wsg-merr', role: 'alert' }, err) : null)
    }

    // New-workspace dialog. A path can always be typed, so creating a workspace
    // never depends on the Host directory-picker backend being available;
    // "Browse…" is the optional convenience on top.
    function PathModal(props) {
      const [value, setValue] = useState('')
      const [busy, setBusy] = useState(false)
      const [err, setErr] = useState(null)
      const [listing, setListing] = useState(null)
      const [showHidden, setShowHidden] = useState(false)
      async function browse(path) {
        const picker = ctx.remote !== undefined ? ctx.remote.directoryPicker : undefined
        if (picker === undefined) { setErr(tm('pickerUnavailable')); return }
        setErr(null); setBusy(true)
        try {
          // Background/remote hosts supply list(), not a native OS dialog.
          // Only an unavailable capability warrants trying the native verb;
          // unreadable paths and other failures must remain visible.
          if (typeof picker.list === 'function') {
            const result = await picker.list(path)
            if (result !== undefined && result.ok === true) {
              setListing(result.value)
              setValue(result.value.path)
              return
            }
            if (!result || !result.error || result.error.code !== 'directory-picker/unavailable') {
              throw new Error(result && result.error && result.error.message || tm('pickerUnavailable'))
            }
          }
          if (typeof picker.pick !== 'function') throw new Error(tm('pickerUnavailable'))
          const result = await picker.pick()
          if (!result || result.ok !== true) {
            throw new Error(result && result.error && result.error.message || tm('pickerUnavailable'))
          }
          if (result.value !== null && result.value !== undefined) setValue(result.value)
        } catch (reason) {
          setErr(reason instanceof Error ? reason.message : String(reason))
        } finally {
          setBusy(false)
        }
      }
      function confirm() {
        const trimmed = value.trim()
        if (trimmed === '' || busy) return
        setBusy(true); setErr(null)
        Promise.resolve(props.onConfirm(trimmed)).then(() => { setBusy(false) }, (reason) => {
          setBusy(false)
          setErr(reason instanceof Error ? reason.message : String(reason))
        })
      }
      return h(Modal, {
        open: true, t: props.t, title: props.title, confirmLabel: tm('create'),
        disabled: busy || value.trim() === '', onClose: props.onClose, onConfirm: confirm,
      },
        h('div', { className: 'wsg-pathrow' },
          h('input', {
            className: 'wsg-input wsg-pathinput', value: value, autoFocus: true,
            'aria-label': tm('workspacePath'), placeholder: tm('workspacePathPlaceholder'), disabled: busy,
            onChange: (e) => setValue(e.target.value),
            onKeyDown: (e) => { if (e.key === 'Enter') { e.preventDefault(); confirm() } },
          }),
          h('button', { type: 'button', className: 'wsg-obtn', disabled: busy, onClick: () => browse(value.trim() || undefined) }, tm('browse'))),
        listing !== null ? h('div', { className: 'wsg-folderbrowser' },
          h('div', { className: 'wsg-pathrow' },
            h('button', { type: 'button', className: 'wsg-obtn', disabled: busy, onClick: () => browse(listing.home) }, tm('home')),
            h('button', { type: 'button', className: 'wsg-obtn', disabled: busy || listing.crumbs.length < 2,
              onClick: () => browse(listing.crumbs[listing.crumbs.length - 2].path) }, tm('parentFolder')),
            h('label', null, h('input', { type: 'checkbox', checked: showHidden, onChange: (e) => setShowHidden(e.target.checked) }), tm('showHidden'))),
          h('div', { role: 'group', 'aria-label': tm('folderList'), style: { maxHeight: '240px', overflowY: 'auto', display: 'grid', gap: '4px', marginTop: '8px' } },
            listing.entries.filter((entry) => showHidden || !entry.hidden).map((entry) =>
              h('button', { key: entry.path, type: 'button', className: 'wsg-obtn', disabled: busy, style: { textAlign: 'left' }, onClick: () => browse(entry.path) }, entry.name)),
            listing.entries.filter((entry) => showHidden || !entry.hidden).length === 0 ? h('div', { className: 'wsg-mdesc' }, tm('emptyDirectory')) : null),
          listing.truncated ? h('div', { className: 'wsg-mdesc' }, tm('truncatedFolders')) : null) : null,
        props.hint !== undefined ? h('div', { className: 'wsg-mdesc' }, props.hint) : null,
        err !== null ? h('div', { className: 'wsg-merr', role: 'alert' }, err) : null)
    }

    function SessionRow(props) {
      const node = props.node; const api = props.api; const t = api.t
      const selected = node.id === api.current
      const st = statusView(node, t)
      const [menuOpen, setMenuOpen] = useState(false)
      const title = node.blank === true ? t('session.new') : node.title
      return h('div', {
        className: 'wsg-row' + (selected ? ' wsg-sel' : '') + (menuOpen ? ' wsg-open' : ''),
        style: { paddingLeft: 0 }, role: 'treeitem', 'aria-selected': selected,
        onMouseDown: (e) => { api.beginDrag('session', node.id, title, e) },
        onClick: () => api.openSession(node.id), title,
      },
        h('span', { className: 'wsg-glyph', 'aria-label': st !== undefined ? st.label : t('status.idle') },
          st !== undefined ? h('span', { className: 'wsg-dot wsg-dot-' + st.state }) : null),
        h('span', { className: 'wsg-name' }, title),
        node.blank !== true ? h('span', { className: 'wsg-time' }, timeLabel(node.updatedAt, api.now, t)) : null,
        node.blank !== true ? h('span', { className: 'wsg-acts' }, h(Menu, {
          label: t('actions.session.aria', { name: title }), onOpenChange: setMenuOpen,
          items: [
            { id: 'rename', label: t('rename'), run: () => api.renameSession(node.id, node.displayTitle) },
            { id: 'fork', label: t('menu.fork'), run: () => api.forkSession(node.id) },
            { id: 'archive', label: t('menu.archiveSession'), run: () => api.archiveSession(node.id) },
          ],
        })) : null)
    }

    function WorkspaceBlock(props) {
      const g = props.g; const depth = props.depth; const api = props.api; const t = api.t
      const doc = api.doc
      const expanded = doc.expanded[g.key] === true
      const active = expanded && g.key === api.currentGroupKey
      const [menuOpen, setMenuOpen] = useState(false)
      const all = api.showAll[g.key] === true
      const shown = expanded === true ? (all ? g.nodes : g.nodes.slice(0, LIMIT5)) : []
      const hiddenCount = expanded === true && !all ? Math.max(0, g.nodes.length - LIMIT5) : 0
      const gid = doc.assignment[g.workspaceId]
      const menuItems = [
        { id: 'rename', label: t('rename'), run: () => api.renameWorkspace(g.workspaceId, g.label) },
        { id: 'up', label: tm('moveUp'), run: () => api.moveWorkspace(g.workspaceId, -1) },
        { id: 'down', label: tm('moveDown'), run: () => api.moveWorkspace(g.workspaceId, +1) },
        { sep: true, id: 's1' },
      ]
      if (gid !== undefined) menuItems.push({ id: 'ungroup', label: tm('ungroup'), run: () => api.assignTo(g.workspaceId, undefined) })
      for (const mg of doc.groups) {
        if (mg.id === gid) continue
        menuItems.push({ id: 'g-' + mg.id, label: '→ ' + mg.name, run: () => api.assignTo(g.workspaceId, mg.id) })
      }
      if (g.workspaceId !== undefined) {
        if (doc.groups.length > 0) menuItems.push({ sep: true, id: 's2' })
        menuItems.push({ id: 'del', label: t('delete.workspace'), danger: true, run: () => api.deleteWorkspace(g.workspaceId, g.label) })
      }
      return h('div', { key: g.key },
        h('div', {
          className: 'wsg-row' + (active ? ' wsg-active' : '') + (menuOpen ? ' wsg-open' : '') + (api.dragWid === g.workspaceId || (api.dragSid !== undefined && g.nodes.some((n) => n.id === api.dragSid)) ? ' wsg-dragging' : ''),
          style: { paddingLeft: depth }, role: 'treeitem', 'aria-expanded': expanded,
          onMouseDown: g.workspaceId !== undefined ? (e) => api.beginDrag('workspace', g.workspaceId, g.label, e) : undefined,
          onClick: () => {
            // A completed drag swallows the click that follows the release.
            if (Date.now() - api.suppressRef.current < 350) return
            api.toggleGroup(g.key)
          },
          title: g.cwd !== undefined ? g.cwd : undefined,
        },
          h('span', { className: 'wsg-glyph' }, icoChevron(expanded)),
          h('span', { className: 'wsg-glyph' }, icoFolder(15)),
          h('span', { className: 'wsg-name' }, g.label),
          h('span', { className: 'wsg-acts' },
            g.workspaceId !== undefined ? h(Menu, { label: t('actions.workspace.aria', { name: g.label }), onOpenChange: setMenuOpen, items: menuItems }) : null,
            g.workspaceId !== undefined ? h('button', {
              type: 'button', className: 'wsg-btn', 'aria-label': t('actions.newSession.aria', { name: g.label }), title: t('actions.newSession.aria', { name: g.label }),
              onClick: (e) => { e.stopPropagation(); api.newSession(g.key, g.workspaceId) },
            }, icoPlus(15)) : null)),
        expanded === true ? h('div', { style: { paddingLeft: 0 } }, shown.map((n) => h(SessionRow, { key: n.id, node: n, api: api }))) : null,
        hiddenCount > 0 ? h('button', {
          type: 'button', className: 'wsg-more', style: { marginLeft: depth + 22 },
          onClick: () => api.setShowAll(g.key, true),
        }, t('sessions.expand', { n: hiddenCount })) : null,
        expanded === true && all && g.nodes.length > LIMIT5 ? h('button', {
          type: 'button', className: 'wsg-more', style: { marginLeft: depth + 22 },
          onClick: () => api.setShowAll(g.key, false),
        }, t('sessions.collapse')) : null)
    }

    function MetaBlock(props) {
      const mg = props.mg; const idx = props.idx; const api = props.api; const t = api.t
      const collapsed = api.doc.metaCollapsed[mg.id] === true
      const members = api.assigned[mg.id] || []
      const total = members.reduce((n, g) => n + g.nodes.length, 0)
      const contains = api.currentGroupKey !== undefined && members.some((g) => g.key === api.currentGroupKey)
      const [menuOpen, setMenuOpen] = useState(false)
      // Drop target for the pointer drag: the whole meta folder accepts a
      // dragged workspace folder (the pointer drag hit-tests [data-meta]).
      const over = api.overMeta === mg.id
      const dragging = api.dragWid !== undefined || api.dragSid !== undefined
      const accent = mg.color !== undefined ? mg.color : 'var(--dsw-alias-brand-primary)'
      const tint = mg.color !== undefined ? { color: mg.color } : undefined
      return h('div', {
        key: mg.id, style: { marginTop: 6, '--wsg-accent': accent }, 'data-meta': mg.id,
        className: over ? 'wsg-drop' : (dragging ? 'wsg-drop-hint' : undefined),
      },
        h('div', {
          className: 'wsg-row' + (!collapsed && contains ? ' wsg-active' : '') + (menuOpen ? ' wsg-open' : '') + (over ? ' wsg-over' : ''),
          style: { paddingLeft: 2 }, role: 'treeitem', 'aria-expanded': !collapsed,
          onClick: () => api.toggleMeta(mg.id), title: mg.name,
        },
          h('span', { className: 'wsg-glyph' }, icoChevron(!collapsed)),
          h('span', { className: 'wsg-glyph', style: tint }, icoGroup(16)),
          h('span', { className: 'wsg-name', style: tint }, mg.name),
          h('span', { className: 'wsg-count' }, total === 0 ? tm('emptyGroup') : t(total === 1 ? 'sessions.count.one' : 'sessions.count.other', { n: total })),
          h('span', { className: 'wsg-acts' }, h(Menu, {
            label: tm('groupActions', { name: mg.name }), onOpenChange: setMenuOpen,
            items: [
              { id: 'rename', label: tm('renameGroup'), run: () => api.renameGroup(mg.id, mg.name, mg.color) },
              { id: 'up', label: tm('moveUp'), run: () => api.moveGroup(idx, -1) },
              { id: 'down', label: tm('moveDown'), run: () => api.moveGroup(idx, +1) },
              // Create a real workspace and file it straight into this folder.
              { id: 'addws', label: tm('newWorkspaceHere'), run: () => api.addWorkspaceInto(mg.id, mg.name) },
              { sep: true, id: 'sep' },
              { id: 'del', label: tm('deleteGroup'), danger: true, run: () => api.deleteGroup(mg.id, mg.name) },
            ],
          }))),
        !collapsed ? h('div', null, members.map((g) => h(WorkspaceBlock, { key: g.key, g, depth: 12, api: api }))) : null)
    }

    function SearchRows(props) {
      const items = props.items; const api = props.api; const t = api.t
      return h('div', { role: 'tree', 'aria-label': t('search.results.aria') },
        items.map((r) => {
          const st = statusView(r, t)
          return h('button', {
            type: 'button', key: r.id, className: 'wsg-result' + (r.id === api.current ? ' wsg-sel' : ''),
            role: 'treeitem', onClick: () => api.openSession(r.id),
          },
            h('span', { className: 'wsg-rhead' },
              h('span', { className: 'wsg-glyph' }, st !== undefined ? h('span', { className: 'wsg-dot wsg-dot-' + st.state }) : null),
              h('span', { className: 'wsg-name' }, r.title)),
            h('span', { className: 'wsg-rmeta' },
              h('span', null, r.workspace),
              r.snippet !== undefined ? h('span', null, r.snippet) : null))
        }),
        items.length === 0 && props.pending ? h('div', { className: 'wsg-empty', role: 'status' }, t('search.pending')) : null,
        props.failed ? h('div', { className: 'wsg-empty', role: 'status' }, t('search.unavailable')) : null,
        items.length === 0 && !props.pending && !props.failed ? h('div', { className: 'wsg-empty' }, t('search.noMatches')) : null,
        props.more ? h('div', { className: 'wsg-empty', role: 'status' }, t('search.hasMore', { n: props.limit })) : null)
    }

    // ---------- the browser ----------
    function Browser(props) {
      const t = props.t
      const wide = props.wide === true
      const list = props.useSessions((s) => s)
      const wsState = props.useWorkspaces((s) => s)
      const wss = wsState.items

      // Pending user interactions ride a framework standard hook: a snapshot
      // map keyed by Session id. Only the three presentable kinds are surfaced.
      const pendingMap = typeof props.useSessionPendingInteraction === 'function' ? props.useSessionPendingInteraction((s) => s) : undefined
      function pendingOf(sid) {
        if (pendingMap === undefined || pendingMap === null || typeof pendingMap.get !== 'function') return undefined
        const it = pendingMap.get(sid)
        const kind = it !== undefined && it !== null && typeof it === 'object' ? it.kind : undefined
        return kind === 'approval' || kind === 'plan-review' || kind === 'question' ? kind : undefined
      }

      const [doc, setDoc] = useState(readDoc)
      useEffect(() => {
        let live = true
        loadDoc().then((next) => { if (live && next !== undefined) setDoc(next) }, () => {})
        return () => { live = false }
      }, [])
      // View state, mirroring the shipped browser's two view options so the
      // meta-folder layer is additive: Workspace/Flat grouping and
      // Manual/Updated session order.
      const groupBy = doc.groupBy === 'flat' ? 'flat' : 'workspace'
      const orderBy = doc.orderBy === 'updated' ? 'updated' : 'manual'
      function setView(patch) { update((prev) => Object.assign({}, prev, patch)) }
      function update(mut) {
        setDoc((prev) => { const next = mut(prev); saveDoc(next); return next })
      }

      const [query, setQuery] = useState('')
      const [searchExpanded, setSearchExpanded] = useState(false)
      const [remote, setRemote] = useState({ q: '', status: 'idle', items: [], hasMore: false })
      const [nameModal, setNameModal] = useState(null)
      const [confirmModal, setConfirmModal] = useState(null)
      const [pathModal, setPathModal] = useState(null)
      const [showAllMap, setShowAllMap] = useState({})
      // Pointer drag state. Native HTML5 drag-and-drop proved unreliable in
      // this host (dragstart fired, then the drag was cancelled before any
      // dragover), so the browser owns the gesture with plain mouse events.
      const [dragWid, setDragWid] = useState(undefined)
      const [dragSid, setDragSid] = useState(undefined)
      const [overMeta, setOverMeta] = useState(undefined)
      const [overList, setOverList] = useState(false)
      const dragRef = React.useRef(null)
      const ghostRef = React.useRef(null)
      const suppressRef = React.useRef(0)
      const apiRef = React.useRef(null)
      const dragHandlersRef = React.useRef(null)

      const nq = sanitize(query).trim()

      useEffect(() => {
        if (nq === '') { setRemote({ q: '', status: 'idle', items: [], hasMore: false }); return undefined }
        const controller = new AbortController()
        setRemote({ q: nq, status: 'loading', items: [], hasMore: false })
        const timer = window.setTimeout(() => {
          Promise.resolve(props.searchSessions(nq, controller.signal)).then((res) => {
            if (controller.signal.aborted) return
            setRemote({ q: nq, status: 'ready', items: res.items, hasMore: res.hasMore === true })
          }, () => { if (!controller.signal.aborted) setRemote({ q: nq, status: 'error', items: [], hasMore: false }) })
        }, SEARCH_MS)
        return () => { window.clearTimeout(timer); try { controller.abort() } catch (e) { /* noop */ } }
      }, [nq, props.searchSessions])

      // auto-expand the current session's group until the user decides otherwise
      const current = list.current
      let currentGroupKey = undefined
      if (current !== undefined) {
        currentGroupKey = ''
        for (const w of wss) { if (w.sessionIds.indexOf(current) !== -1) { currentGroupKey = w.workspaceId; break } }
      }
      useEffect(() => {
        if (currentGroupKey === undefined) return
        setDoc((prev) => {
          if (Object.prototype.hasOwnProperty.call(prev.expanded, currentGroupKey)) return prev
          const next = Object.assign({}, prev, { expanded: Object.assign({}, prev.expanded, { [currentGroupKey]: true }) })
          saveDoc(next)
          return next
        })
      }, [currentGroupKey])

      // ---- derivations ----
      const now = Date.now()
      const archived = new Set(Array.from(wsState.archivedSessionIds || []))
      function visible(s) { return s.origin !== 'subagent' && !archived.has(s.id) && (!s.blank || s.id === current) }
      function titleOf(s) { return s.blank ? 'New Session' : s.displayTitle }

      const subCache = {}
      const childrenBy = {}
      for (const id in list.byId) {
        const s = list.byId[id]
        if (s.origin === 'subagent' && s.parentId !== undefined) {
          if (childrenBy[s.parentId] === undefined) childrenBy[s.parentId] = []
          childrenBy[s.parentId].push(id)
        }
      }
      function subRunning(pid, guard) {
        if (subCache[pid] !== undefined) return subCache[pid]
        if (guard.has(pid)) return 0
        guard.add(pid)
        let n = 0
        const kids = childrenBy[pid] !== undefined ? childrenBy[pid] : []
        for (const cid of kids) {
          const c = list.byId[cid]
          if (c === undefined) continue
          if (c.running === true) n += 1
          n += subRunning(cid, guard)
        }
        subCache[pid] = n
        return n
      }

      function nodesOf(ids, accountKey) {
        const arr = []
        for (const id of ids) {
          const s = list.byId[id]
          if (s === undefined || !visible(s)) continue
          arr.push({
            id: s.id, title: titleOf(s), displayTitle: s.displayTitle !== undefined ? s.displayTitle : '',
            blank: s.blank === true, running: s.running === true, completed: s.completed === true,
            pendingInteraction: pendingOf(s.id), subCount: subRunning(s.id, new Set()), updatedAt: s.updatedAt,
          })
        }
        const stored = shippedAccounts[accountKey]
        if (orderBy === 'manual' && Array.isArray(stored)) {
          const byId2 = new Map(arr.map((n) => [n.id, n]))
          const used = new Set()
          const out = []
          for (const k of stored) { const n = byId2.get(k); if (n !== undefined && !used.has(k)) { out.push(n); used.add(k) } }
          return out.concat(arr.filter((n) => !used.has(n.id)).sort(byRecency))
        }
        arr.sort(byRecency)
        return arr
      }

      const wsGroups = []
      const accounted = new Set()
      for (const w of wss) {
        for (const sid of w.sessionIds) accounted.add(sid)
        wsGroups.push({
          key: w.workspaceId, workspaceId: w.workspaceId, cwd: w.path,
          label: w.title !== undefined && w.title !== '' ? w.title : workspaceLabel(w.path),
          nodes: nodesOf(w.sessionIds, w.workspaceId),
        })
      }
      const strayIds = (list.ids || []).filter((id) => list.byId[id] !== undefined && !accounted.has(id) && visible(list.byId[id]))
      const ungrouped = strayIds.length > 0 ? { key: '', workspaceId: undefined, cwd: undefined, label: t('group.ungrouped'), nodes: nodesOf(strayIds, '') } : null

      const groupIds = new Set(doc.groups.map((g) => g.id))
      const assigned = {}
      const plain = []
      for (const g of wsGroups) {
        const gid = doc.assignment[g.workspaceId]
        if (gid !== undefined && groupIds.has(gid)) { if (assigned[gid] === undefined) assigned[gid] = []; assigned[gid].push(g) } else plain.push(g)
        for (const n of g.nodes) {
          const sidGroup = (doc.sessionAssignment || {})[n.id]
          if (sidGroup !== undefined && groupIds.has(sidGroup)) {
            if (assigned[sidGroup] === undefined) assigned[sidGroup] = []
            assigned[sidGroup].push({ key: 'session:' + n.id, workspaceId: undefined, cwd: g.cwd, label: g.label, nodes: [n] })
          }
        }
      }

      // Flat view: one list of every visible session, using the shipped flat
      // account key so an already-arranged flat order carries over.
      const flatNodes = groupBy === 'flat' ? nodesOf((list.ids || []), '__flat_session_order__') : []

      // ---- api passed to stable child components ----
      const api = {
        t, now, current, currentGroupKey, doc, assigned, showAll: showAllMap,
        dragWid: dragWid, setDragWid: setDragWid, dragSid: dragSid, setDragSid: setDragSid, overMeta: overMeta, overList: overList, suppressRef: suppressRef,
        beginDrag: (kind, id, label, e) => { const h2 = dragHandlersRef.current; if (h2 !== null) h2.begin(kind, id, label, e) },
        openSession: (sid) => { sessions.open(sid) },
        newSession: (key, wid) => { update((prev) => (prev.expanded[key] === true ? prev : Object.assign({}, prev, { expanded: Object.assign({}, prev.expanded, { [key]: true }) }))); startSessionIn(wid) },
        addWorkspaceInto: (gid2, name) => openNewWorkspace(gid2, name),
        toggleGroup: (key) => update((prev) => Object.assign({}, prev, { expanded: Object.assign({}, prev.expanded, { [key]: prev.expanded[key] !== true }) })),
        toggleMeta: (gid2) => update((prev) => Object.assign({}, prev, { metaCollapsed: Object.assign({}, prev.metaCollapsed, { [gid2]: prev.metaCollapsed[gid2] !== true }) })),
        setShowAll: (key, v) => setShowAllMap((prev) => Object.assign({}, prev, { [key]: v })),
        renameSession: (sid, cur) => setNameModal({ kind: 'renameSession', id: sid, initial: cur, title: t('rename.session.title') }),
        forkSession: (sid) => { Promise.resolve(sessions.fork({ sessionId: sid, increaseTitle: true })).then((cid) => sessions.open(cid), () => {}) },
        archiveSession: (sid) => { Promise.resolve(workspaces.archiveSession(sid)).catch((r) => console.error('archive failed', r)) },
        renameWorkspace: (wid, cur) => setNameModal({ kind: 'renameWorkspace', id: wid, initial: cur, title: t('rename.workspace.title') }),
        deleteWorkspace: (wid, label) => setConfirmModal({
          title: t('delete.workspace'), desc: t('delete.desc', { name: label }), confirmLabel: t('delete.workspace'), danger: true,
          run: () => Promise.resolve(workspaces.delete(wid)),
        }),
        moveWorkspace: (wid, delta) => {
          const ids = wss.map((w) => w.workspaceId)
          const i = ids.indexOf(wid)
          if (i === -1) return
          const j = i + delta
          if (j < 0 || j >= ids.length) return
          const anchor = delta === -1 ? ids[i - 1] : (i + 2 < ids.length ? ids[i + 2] : undefined)
          Promise.resolve(workspaces.insertBefore(wid, anchor)).catch((r) => console.error('reorder failed', r))
        },
        assignTo: (wid, gid2) => update((prev) => {
          const assignment = Object.assign({}, prev.assignment)
          if (gid2 === undefined) delete assignment[wid]; else assignment[wid] = gid2
          return Object.assign({}, prev, { assignment })
        }),
        assignSessionTo: (sid, gid2) => update((prev) => {
          const sessionAssignment = Object.assign({}, prev.sessionAssignment || {})
          if (gid2 === undefined) delete sessionAssignment[sid]; else sessionAssignment[sid] = gid2
          return Object.assign({}, prev, { sessionAssignment })
        }),
        renameGroup: (gid2, cur, color) => setNameModal({ kind: 'renameGroup', id: gid2, initial: cur, color: color, title: tm('renameGroup') }),
        deleteGroup: (gid2, name) => setConfirmModal({ title: tm('deleteGroup'), desc: tm('deleteGroupDesc'), confirmLabel: tm('deleteGroup'), danger: true, run: () => { deleteGroup(gid2) } }),
        moveGroup: (idx, delta) => update((prev) => {
          const j = idx + delta
          if (j < 0 || j >= prev.groups.length) return prev
          const groups = prev.groups.slice()
          const tmp = groups[idx]; groups[idx] = groups[j]; groups[j] = tmp
          return Object.assign({}, prev, { groups })
        }),
      }
      // Keep the latest api reachable from the one-time document listeners.
      apiRef.current = api

      // ---- pointer drag: press a workspace row, move onto a meta folder ----
      React.useEffect(() => {
        function removeGhost() {
          const g = ghostRef.current
          if (g !== null && g.parentNode !== null) g.parentNode.removeChild(g)
          ghostRef.current = null
        }
        function clearListeners() {
          document.removeEventListener('mousemove', onMove, true)
          document.removeEventListener('mouseup', onUp, true)
          document.removeEventListener('keydown', onKey, true)
        }
        function finish(x, y, cancelled) {
          const st = dragRef.current
          dragRef.current = null
          clearListeners()
          removeGhost()
          document.body.style.userSelect = ''
          const a = apiRef.current
          if (st !== null && st.active === true) {
            // Swallow the click that follows the release.
            suppressRef.current = Date.now()
            if (cancelled !== true && a !== null) {
              let metaId
              let onList = false
              try {
                const el = document.elementFromPoint(x, y)
                if (el !== null) {
                  const m = el.closest('[data-meta]')
                  metaId = m !== null ? m.getAttribute('data-meta') : undefined
                  onList = el.closest('.wsg-list') !== null
                }
              } catch (e) { /* pointer left the document */ }
              if (metaId !== undefined && metaId !== null && metaId !== '') st.kind === 'session' ? a.assignSessionTo(st.id, metaId) : a.assignTo(st.id, metaId)
              else if (onList) st.kind === 'session' ? a.assignSessionTo(st.id, undefined) : a.assignTo(st.id, undefined)
            }
          }
          setDragWid(undefined); setDragSid(undefined); setOverMeta(undefined); setOverList(false)
        }
        function onMove(e) {
          const st = dragRef.current
          if (st === null) return
          if (st.active !== true) {
            if (Math.abs(e.clientX - st.x) < 5 && Math.abs(e.clientY - st.y) < 5) return
            st.active = true
            document.body.style.userSelect = 'none'
            const g = document.createElement('div')
            g.className = 'wsg-ghost'
            g.textContent = st.label
            document.body.appendChild(g)
            ghostRef.current = g
            if (st.kind === 'session') setDragSid(st.id); else setDragWid(st.id)
          }
          const gh = ghostRef.current
          if (gh !== null) gh.style.transform = 'translate(' + (e.clientX + 12) + 'px,' + (e.clientY + 10) + 'px)'
          try {
            const el = document.elementFromPoint(e.clientX, e.clientY)
            const m = el !== null ? el.closest('[data-meta]') : null
            const id = m !== null ? m.getAttribute('data-meta') : undefined
            setOverMeta((prev) => (prev === id ? prev : id))
            setOverList(el !== null && (id === undefined || id === null) && el.closest('.wsg-list') !== null)
          } catch (e2) { /* pointer left the document */ }
        }
        function onUp(e) { finish(e.clientX, e.clientY, false) }
        function onKey(e) { if (e.key === 'Escape') finish(0, 0, true) }
        dragHandlersRef.current = {
          begin: (kind, id, label, e) => {
            if (e.button !== 0) return
            const target = e.target
            if (target !== null && target.closest !== undefined && target.closest('button,input,a,textarea') !== null) return
            dragRef.current = { kind: kind, id: id, label: label, x: e.clientX, y: e.clientY, active: false }
            document.addEventListener('mousemove', onMove, true)
            document.addEventListener('mouseup', onUp, true)
            document.addEventListener('keydown', onKey, true)
          },
        }
        return () => { clearListeners(); removeGhost() }
      }, [])
      function deleteGroup(gid2) {
        update((prev) => {
          const assignment = {}
          for (const k in prev.assignment) if (prev.assignment[k] !== gid2) assignment[k] = prev.assignment[k]
          return Object.assign({}, prev, { groups: prev.groups.filter((g) => g.id !== gid2), assignment })
        })
      }

      // ---- search merge (port of the shipped deriveSearchResults) ----
      const resultLimit = typeof props.searchResultLimit === 'number' ? props.searchResultLimit : 20
      function mergedResults() {
        const q = nq.toLowerCase()
        const wsBySession = new Map()
        for (const w of wss) for (const sid of w.sessionIds) if (!wsBySession.has(sid)) wsBySession.set(sid, w.title !== undefined && w.title !== '' ? w.title : workspaceLabel(w.path))
        const fresh = remote.q === nq && remote.status === 'ready'
        const remoteItems = fresh ? remote.items : []
        const snippetBy = new Map()
        for (const it of remoteItems) if (!snippetBy.has(it.sessionId)) snippetBy.set(it.sessionId, it.snippet)
        const labelOf = (s) => (wsBySession.has(s.id) ? wsBySession.get(s.id) : workspaceLabel(s.cwd))
        const local = []
        for (const id of list.ids) {
          const s = list.byId[id]
          if (s === undefined || s.blank === true || !visible(s)) continue
          if (titleOf(s).toLowerCase().indexOf(q) !== -1 || labelOf(s).toLowerCase().indexOf(q) !== -1) local.push(s)
        }
        local.sort(byRecency)
        const seen = new Set()
        const ordered = []
        const inc = (s) => { if (seen.has(s.id)) return; seen.add(s.id); ordered.push(s) }
        local.forEach(inc)
        for (const it of remoteItems) { const s = list.byId[it.sessionId]; if (s !== undefined && s.blank !== true && visible(s)) inc(s) }
        return ordered.slice(0, resultLimit).map((s) => ({
          id: s.id, title: titleOf(s), workspace: labelOf(s), running: s.running === true,
          completed: s.completed === true, pendingInteraction: pendingOf(s.id),
          subCount: subRunning(s.id, new Set()), snippet: snippetBy.get(s.id),
        }))
      }

      // ---- dialogs ----
      function dialog() {
        if (pathModal !== null) {
          return h(PathModal, {
            key: 'nw', t, title: pathModal.title, hint: tm('newWorkspaceHint'),
            onClose: () => setPathModal(null),
            onConfirm: (path2) => createWorkspaceAt(path2, pathModal.metaId),
          })
        }
        if (nameModal !== null) {
          if (nameModal.kind === 'renameWorkspace') {
            return h(NameModal, {
              key: 'rw' + nameModal.id, t, title: nameModal.title, initial: nameModal.initial, confirmLabel: t('rename'), fieldLabel: t('field.workspaceName'),
              onClose: () => setNameModal(null),
              onConfirm: (name) => Promise.resolve(workspaces.rename(nameModal.id, name)).then(() => setNameModal(null)),
            })
          }
          if (nameModal.kind === 'renameSession') {
            return h(NameModal, {
              key: 'rs' + nameModal.id, t, title: nameModal.title, initial: nameModal.initial, confirmLabel: t('rename'), fieldLabel: t('field.sessionName'),
              onClose: () => setNameModal(null),
              onConfirm: (name) => {
                const binding = sessions.binding(nameModal.id)
                if (binding === undefined || binding.session === undefined) return Promise.reject(new Error('unknown session'))
                return Promise.resolve(binding.session.rename(name)).then((result) => {
                  if (result !== undefined && result.ok === false) throw new Error((result.error && result.error.message) || 'rename failed')
                  setNameModal(null)
                })
              },
            })
          }
          if (nameModal.kind === 'renameGroup') {
            return h(NameModal, {
              key: 'rg' + nameModal.id, t, title: nameModal.title, initial: nameModal.initial, confirmLabel: t('rename'),
              withColor: true, color: nameModal.color,
              onClose: () => setNameModal(null),
              onConfirm: (name, color) => {
                update((prev) => Object.assign({}, prev, { groups: prev.groups.map((g) => { if (g.id === nameModal.id) return { id: g.id, name, color }; return g }) }))
                setNameModal(null)
                return Promise.resolve()
              },
            })
          }
          return h(NameModal, {
            key: 'ng', t, title: tm('newGroup'), initial: '', confirmLabel: tm('create'),
            withColor: true, color: undefined,
            onClose: () => setNameModal(null),
            onConfirm: (name, color) => {
              const id = 'g' + Date.now().toString(36) + Math.floor(Math.random() * 1e4).toString(36)
              update((prev) => Object.assign({}, prev, { groups: prev.groups.concat([{ id, name, color }]) }))
              setNameModal(null)
              return Promise.resolve()
            },
          })
        }
        if (confirmModal !== null) {
          return h(Modal, {
            open: true, t, title: confirmModal.title, desc: confirmModal.desc, confirmLabel: confirmModal.confirmLabel, danger: confirmModal.danger === true,
            onClose: () => setConfirmModal(null),
            onConfirm: () => { Promise.resolve(confirmModal.run()).then(() => setConfirmModal(null), (r) => { setConfirmModal(null); console.error('action failed:', r) }) },
          })
        }
        return null
      }

      // ---- new-workspace flow ----
      // A dialog where the folder path is typed (or browsed for). Typing always
      // works, so creating a workspace no longer depends on the Host directory
      // picker backend being available. `metaId` files the new workspace
      // straight into that meta folder.
      function openNewWorkspace(metaId, metaName) {
        setPathModal({
          metaId: metaId,
          title: metaId !== undefined ? tm('newWorkspaceInTitle', { name: metaName }) : tm('newWorkspaceTitle'),
        })
      }
      function onAddWorkspace() { openNewWorkspace(undefined) }
      function createWorkspaceAt(path2, metaId) {
        return Promise.resolve(workspaces.create({ path: path2 })).then((w) => {
          if (metaId !== undefined) {
            update((prev) => Object.assign({}, prev, {
              assignment: Object.assign({}, prev.assignment, { [w.workspaceId]: metaId }),
              metaCollapsed: Object.assign({}, prev.metaCollapsed, { [metaId]: false }),
            }))
          }
          setPathModal(null)
          startSessionIn(w.workspaceId)
        })
      }

      // ---- rail (collapsed sidebar) ----
      if (!wide) {
        return h('div', { className: 'wsg-root' },
          h('div', { className: 'wsg-head wsg-head-rail' },
            h('button', { type: 'button', className: 'wsg-btn', 'aria-label': t('search.sessions.aria'), title: t('search.sessions.aria'), onClick: () => { if (props.expandSidebar !== undefined) props.expandSidebar() } }, icoSearch(16)),
            h('button', {
              type: 'button', className: 'wsg-btn wsg-newgroup', 'aria-label': tm('addGroup'), title: tm('addGroup'),
              onClick: () => { if (props.expandSidebar !== undefined) props.expandSidebar(); setNameModal({ kind: 'newGroup', initial: '', title: tm('newGroup') }) },
            }, icoFolderPlus(16)),
            h('button', { type: 'button', className: 'wsg-btn', 'aria-label': t('workspace.add'), title: t('workspace.add'), onClick: onAddWorkspace }, icoProjectAdd(16))),
          dialog())
      }

      // ---- full view ----
      const sections = []
      doc.groups.forEach((mg, i) => sections.push(h(MetaBlock, { key: mg.id, mg, idx: i, api })))
      for (const g of plain) sections.push(h(WorkspaceBlock, { key: g.key, g, depth: 6, api }))
      if (ungrouped !== null) sections.push(h(WorkspaceBlock, { key: '', g: ungrouped, depth: 6, api }))
      const emptyAll = doc.groups.length === 0 && plain.length === 0 && ungrouped === null

      return h('div', { className: 'wsg-root' },
        h('div', { className: 'wsg-head' },
          nq !== '' || searchExpanded ? h('div', { className: 'wsg-searchbox' },
            h('span', { className: 'wsg-glyph' }, icoSearch(12)),
            h('input', {
              ref: undefined, type: 'text', placeholder: t('search.placeholder'), value: query, autoFocus: true,
              onChange: (e) => setQuery(sanitize(e.target.value)),
              onKeyDown: (e) => { if (e.key === 'Escape') { setQuery(''); setSearchExpanded(false) } },
            }),
            h('button', { type: 'button', className: 'wsg-btn', 'aria-label': t('search.clear'), onClick: () => { setQuery(''); setSearchExpanded(false) } }, icoClose(12)))
            : h('span', { className: 'wsg-title' }, t('section.workspaces')),
          nq === '' && !searchExpanded ? h('button', { type: 'button', className: 'wsg-btn', 'aria-label': t('search.sessions.aria'), title: t('search.sessions.aria'), onClick: () => setSearchExpanded(true) }, icoSearch(15)) : null,
          nq === '' && groupBy !== 'flat' ? h('button', { type: 'button', className: 'wsg-btn wsg-newgroup', 'aria-label': tm('addGroup'), title: tm('addGroup'), onClick: () => setNameModal({ kind: 'newGroup', initial: '', title: tm('newGroup') }) }, icoFolderPlus(16)) : null,
          nq === '' ? h(Menu, {
            label: t('viewOptions.label'), icon: icoSliders(16), onOpenChange: () => { },
            items: [
              { header: true, label: t('groupBy.label') },
              { id: 'g-workspace', label: (groupBy === 'workspace' ? '✓  ' : '') + t('groupBy.workspace'), run: () => setView({ groupBy: 'workspace' }) },
              { id: 'g-flat', label: (groupBy === 'flat' ? '✓  ' : '') + t('groupBy.flat'), run: () => setView({ groupBy: 'flat' }) },
              { sep: true, id: 'vo-sep' },
              { header: true, label: t('orderBy.label') },
              { id: 'o-manual', label: (orderBy === 'manual' ? '✓  ' : '') + t('orderBy.manual'), run: () => setView({ orderBy: 'manual' }) },
              { id: 'o-updated', label: (orderBy === 'updated' ? '✓  ' : '') + t('orderBy.updated'), run: () => setView({ orderBy: 'updated' }) },
            ],
          }) : null,
          nq === '' ? h('button', { type: 'button', className: 'wsg-btn', 'aria-label': t('workspace.add'), title: t('workspace.add'), onClick: onAddWorkspace }, icoProjectAdd(16)) : null),
        dragWid !== undefined ? h('div', { className: 'wsg-hint' }, doc.groups.length > 0 ? tm('dndHint') : tm('dndNoMeta')) : null,
        h('div', { className: 'wsg-list' + (overList ? ' wsg-list-drop' : '') },
          nq !== '' ? h(SearchRows, { api, items: mergedResults(), pending: remote.q !== nq || remote.status === 'loading', failed: remote.q === nq && remote.status === 'error', more: remote.q === nq && remote.hasMore === true, limit: resultLimit })
            : groupBy === 'flat' ? (flatNodes.length === 0 ? h('div', { className: 'wsg-empty' }, t('empty.none'))
              : h('div', { role: 'tree', 'aria-label': t('section.sessions') }, flatNodes.map((n) => h(SessionRow, { key: n.id, node: n, api }))))
              : emptyAll ? h('div', { className: 'wsg-empty' }, t('empty.none'))
                : h('div', { role: 'tree', 'aria-label': t('section.sessions') }, sections)),
        dialog())
    }

    // ---------- registration ----------
    const flowHooks = {}
    if (typeof slots.entries === 'function' && typeof slots.subscribe === 'function') {
    }
    // Host facts observable (contract twin of the shipped browser's hostInfo).
    try {
      if (ctx.remote !== undefined && ctx.remote.$host !== undefined) {
        flowHooks.hostInfo = {
          getSnapshot: () => ctx.remote.$host,
          subscribe: (listener) => ctx.on('connection/reset', listener),
        }
      }
    } catch (e) { /* host facts unavailable: useHostInfo just stays absent */ }

    function injectedFace() {
      return {
        searchSessions: async (query, signal) => {
          const result = await sessions.search(query, signal)
          if (result.ok !== true) throw new Error((result.error && result.error.message) || 'search failed')
          return result.value
        },
        searchResultLimit: typeof sessions.searchResultLimit === 'number' ? sessions.searchResultLimit : 20,
        hooks: flowHooks,
      }
    }

    try {
      ctx.effect(() => slots.inject('sidebar.workspaces', () => slots.register({
        name: 'sidebar.workspaces',
        // A single slot accepts one registration per priority and the lowest
        // renders: -1 is what shadows the shipped browser at 0.
        priority: -1,
        // No child hole: the directory-flow hole is declared by the shipped
        // registration too, and depending on it left the add action dead. The
        // Host directory-picker Remote is driven directly instead.
        locale: 'workspace',
        inject: injectedFace,
      }, Browser)), 'wsg:seat')
    } catch (e) {
      console.error('seat registration failed:', e)
    }
  },
}
