module.exports = [
    {
        files: ["**/*.js"],
        rules: {
            "no-unused-vars": "warn",
            "no-console": "off",
            "no-undef": "off"
        },
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "module",
            globals: {
                window: "readonly",
                document: "readonly",
                Nebulus: "readonly",
                localStorage: "readonly",
                console: "readonly",
                fetch: "readonly",
                MutationObserver: "readonly",
                setTimeout: "readonly",
                clearTimeout: "readonly"
            }
        }
    }
];
