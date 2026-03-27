import { type ComponentProps } from 'react';
import { type InnerClassNamesProp } from '../../types';
export type ClearableInputElementKey = 'input' | 'clearButton';
export interface ClearableInputProps extends ComponentProps<'input'> {
    innerClassNames?: InnerClassNamesProp<ClearableInputElementKey>;
    withClearButton?: boolean;
}
export declare const ClearableInput: import("react").ForwardRefExoticComponent<Omit<ClearableInputProps, "ref"> & import("react").RefAttributes<HTMLInputElement>>;
//# sourceMappingURL=ClearableInput.d.ts.map