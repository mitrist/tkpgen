import { type ComponentProps, type ReactNode } from 'react';
export type CellListMode = 'full-width' | 'island';
export interface CellListProps extends ComponentProps<'div'> {
    mode?: CellListMode;
    filled?: boolean;
    header?: ReactNode;
}
export declare const CellList: import("react").ForwardRefExoticComponent<Omit<CellListProps, "ref"> & import("react").RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=CellList.d.ts.map