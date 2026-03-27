import { type ComponentProps } from 'react';
import { type InnerClassNamesProp } from '../../types';
export type TextareaElementKey = 'textarea';
export type TextareaMode = 'primary' | 'secondary';
export interface TextareaProps extends ComponentProps<'textarea'> {
    mode?: TextareaMode;
    innerClassNames?: InnerClassNamesProp<TextareaElementKey>;
}
export declare const Textarea: import("react").ForwardRefExoticComponent<Omit<TextareaProps, "ref"> & import("react").RefAttributes<HTMLTextAreaElement>>;
//# sourceMappingURL=Textarea.d.ts.map