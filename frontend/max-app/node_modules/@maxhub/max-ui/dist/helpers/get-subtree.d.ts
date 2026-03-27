import { type ReactNode } from 'react';
/**
 * This is a helper function that is used when a component supports `asChild`
 * using the `Slot` component but its implementation contains nested DOM elements.
 *
 * Using it ensures if a consumer uses the `asChild` prop, the elements are in
 * correct order in the DOM, adopting the intended consumer `children`.
 *
 * Reference: https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/helpers/get-subtree.ts#L10
 */
export declare const getSubtree: (options: {
    asChild: boolean | undefined;
    children: ReactNode;
}, content: ReactNode | ((children: ReactNode) => ReactNode)) => ReactNode;
//# sourceMappingURL=get-subtree.d.ts.map