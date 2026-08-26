"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LocalStorage = void 0;
const tslib_1 = require("tslib");
const fs_1 = require("fs");
const mime_1 = tslib_1.__importDefault(require("mime"));
const path_1 = require("path");
const axios_1 = tslib_1.__importDefault(require("axios"));
class LocalStorage {
    constructor(uploadDirectory) {
        this.uploadDirectory = uploadDirectory;
    }
    async uploadSimple(path) {
        // PATCH (session #14, trap #46b): provider avatar CDNs (e.g. LinkedIn
        // media) may 403 a bare server-side fetch — a missing profile picture
        // must NEVER abort the whole channel connect.
        let loadImage;
        try {
            loadImage = await axios_1.default.get(path, { responseType: 'arraybuffer' });
        }
        catch (err) {
            return '';
        }
        const contentType = loadImage?.headers?.['content-type'] ||
            loadImage?.headers?.['Content-Type'];
        const findExtension = mime_1.default.getExtension(contentType);
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const innerPath = `/${year}/${month}/${day}`;
        const dir = `${this.uploadDirectory}${innerPath}`;
        (0, fs_1.mkdirSync)(dir, { recursive: true });
        const randomName = Array(32)
            .fill(null)
            .map(() => Math.round(Math.random() * 16).toString(16))
            .join('');
        const filePath = `${dir}/${randomName}.${findExtension}`;
        const publicPath = `${innerPath}/${randomName}.${findExtension}`;
        (0, fs_1.writeFileSync)(filePath, loadImage.data);
        return process.env.FRONTEND_URL + '/uploads' + publicPath;
    }
    async uploadFile(file) {
        try {
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const innerPath = `/${year}/${month}/${day}`;
            const dir = `${this.uploadDirectory}${innerPath}`;
            (0, fs_1.mkdirSync)(dir, { recursive: true });
            const randomName = Array(32)
                .fill(null)
                .map(() => Math.round(Math.random() * 16).toString(16))
                .join('');
            const filePath = `${dir}/${randomName}${(0, path_1.extname)(file.originalname)}`;
            const publicPath = `${innerPath}/${randomName}${(0, path_1.extname)(file.originalname)}`;
            (0, fs_1.writeFileSync)(filePath, file.buffer);
            return {
                filename: `${randomName}${(0, path_1.extname)(file.originalname)}`,
                path: process.env.FRONTEND_URL + '/uploads' + publicPath,
                mimetype: file.mimetype,
                originalname: file.originalname,
            };
        }
        catch (err) {
            console.error('Error uploading file to Local Storage:', err);
            throw err;
        }
    }
    async removeFile(filePath) {
        return new Promise((resolve, reject) => {
            (0, fs_1.unlink)(filePath, (err) => {
                if (err) {
                    reject(err);
                }
                else {
                    resolve();
                }
            });
        });
    }
}
exports.LocalStorage = LocalStorage;
//# sourceMappingURL=local.storage.js.map