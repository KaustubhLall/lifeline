import { useState, useEffect, useCallback } from 'react';

export function useMobileLayout() {
    const [showSidebar, setShowSidebar] = useState(false);
    const [showMobileMenu, setShowMobileMenu] = useState(false);

    // Close mobile menu when clicking outside
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

    const toggleSidebar = useCallback(() => {
        setShowSidebar(prev => !prev);
    }, []);

    const closeSidebar = useCallback(() => {
        setShowSidebar(false);
    }, []);

    const toggleMobileMenu = useCallback(() => {
        setShowMobileMenu(prev => !prev);
    }, []);

    const closeMobileMenu = useCallback(() => {
        setShowMobileMenu(false);
    }, []);

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
