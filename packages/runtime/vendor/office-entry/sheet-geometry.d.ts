/** Calc data-area and A1 coordinates shared by saved-file and retained-session capture. */
export interface CellRange {
    readonly firstColumn: number;
    readonly firstRow: number;
    readonly lastColumn: number;
    readonly lastRow: number;
}
export interface Rectangle {
    readonly x: number;
    readonly y: number;
    readonly width: number;
    readonly height: number;
}
export interface SheetPartInfo {
    readonly name: string;
    readonly visible: number;
    readonly rtllayout: number;
    readonly lastcolumn: number;
    readonly lastrow: number;
}
interface DimensionData {
    readonly sizes: string;
    readonly hidden: string;
    readonly filtered: string;
}
export interface SheetGeometry {
    readonly columns: DimensionData;
    readonly rows: DimensionData;
}
export declare function rangeName(range: CellRange): string;
export declare function parseCellRange(value: string): CellRange;
export declare function sheetPartInfo(value: string): SheetPartInfo;
/** Formatting-only cells and standalone drawings do not enlarge LibreOffice's data area. */
export declare function dataArea(info: SheetPartInfo): CellRange;
/** Logical columns advance from A; LOK itself mirrors RTL sheet painting. No manual x inversion. */
export declare function sheetRangeRectangle(geometry: SheetGeometry, range: CellRange, scale: number): Rectangle;
export {};
