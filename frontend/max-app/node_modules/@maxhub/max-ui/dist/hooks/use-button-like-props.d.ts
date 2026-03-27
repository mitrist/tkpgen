import { type ComponentProps, type ElementType, type ReactNode } from 'react';
export interface ButtonLikeProps {
    asChild?: boolean;
    children?: ReactNode;
    disabled?: boolean;
    loading?: boolean;
    rootElement?: ElementType;
}
export declare const useButtonLikeProps: (props: ButtonLikeProps) => ComponentProps<any>;
//# sourceMappingURL=use-button-like-props.d.ts.map