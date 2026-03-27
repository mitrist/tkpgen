import { type ComponentProps, type ReactNode } from 'react';
import type { InnerClassNamesProp } from '../../types';
export type CellHeaderTitleStyle = 'caps' | 'normal';
export type CellHeaderInnerElementKey = 'content' | 'after';
export interface CellHeaderProps extends ComponentProps<'div'> {
    titleStyle?: CellHeaderTitleStyle;
    fullWidth?: boolean;
    after?: ReactNode;
    innerClassNames?: InnerClassNamesProp<CellHeaderInnerElementKey>;
}
export declare const CellHeader: import("react").ForwardRefExoticComponent<Omit<CellHeaderProps, "ref"> & import("react").RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=CellHeader.d.ts.map