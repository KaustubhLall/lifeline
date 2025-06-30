import {useCallback, useEffect, useState} from 'react';

export function useMobileLayout() {
    const [showSidebar, setShowSidebar] = useState(false);
    const [showMobileMenu, setShowMobileMenu] = useState(false);

    // Hide menus when clicking outside their active elements
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (showMobileMenu && !event.target.closest('.mobile-dropdown')) {
                setShowMobileMenu(false);
            }
            if (showSidebar && !event.target.closest('.sidebar') && !event.target.closest('.menu-button')) {
                setShowSidebar(false);
            }
        };

        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, [showMobileMenu, showSidebar]);

    // Toggle sidebar visibility
    const toggleSidebar = useCallback(() => {
        setShowSidebar(prev => !prev);
    }, []);

    // Close sidebar
    const closeSidebar = useCallback(() => {
        setShowSidebar(false);
    }, []);

    // Toggle mobile settings menu
    const toggleMobileMenu = useCallback(() => {
        setShowMobileMenu(prev => !prev);
    }, []);

    // Close mobile settings menu
    const closeMobileMenu = useCallback(() => {
        setShowMobileMenu(false);
    }, []);

    // Reset all layout states to initial
    const resetLayout = useCallback(() => {
        setShowSidebar(false);
        setShowMobileMenu(false);
    }, []);

    return {
        showSidebar,
        showMobileMenu,
        toggleSidebar,
        closeSidebar,
        toggleMobileMenu,
        closeMobileMenu,
        resetLayout
    };
}
