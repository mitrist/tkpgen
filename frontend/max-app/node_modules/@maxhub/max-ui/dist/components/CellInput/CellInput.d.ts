import { type ComponentProps, type ReactNode } from 'react';
import { type InnerClassNamesProp } from '../../types';
export type CellInputHeight = 'compact' | 'normal';
export type CellInputElementKey = 'before' | 'input' | 'clearButton' | 'body';
export interface CellInputProps extends ComponentProps<'input'> {
    height?: CellInputHeight;
    before?: ReactNode;
    innerClassNames?: InnerClassNamesProp<CellInputElementKey>;
}
export declare const CellInput: import("react").ForwardRefExoticComponent<Omit<CellInputProps, "ref"> & import("react").RefAttributes<HTMLInputElement>>;
//# sourceMappingURL=CellInput.d.ts.map