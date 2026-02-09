import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';

// Map category IDs to folder names
const categoryFolders: Record<string, string> = {
    'polity': 'Polity',
    'economy': 'Economy',
    'environment': 'Environment',
    'science-tech': 'Science-Technology',
    'ir': 'International-Relations',
    'art-culture': 'Art-Culture',
    'social': 'Social-Issues',
    'current-affairs': 'Current-Affairs',
};

export async function GET(
    request: NextRequest,
    { params }: { params: { path: string[] } }
) {
    try {
        const pathSegments = params.path;

        if (!pathSegments || pathSegments.length < 2) {
            return NextResponse.json({ error: 'Invalid path', segments: pathSegments }, { status: 400 });
        }

        const categoryId = pathSegments[0];
        const filename = pathSegments[1];

        const folderName = categoryFolders[categoryId];
        if (!folderName) {
            return NextResponse.json({ error: 'Category not found', categoryId }, { status: 404 });
        }

        // Use absolute path for Windows
        const basePath = 'D:\\ForImpPerson\\upsc-ai-platform\\study-materials';
        const filePath = path.join(basePath, folderName, filename);

        console.log('File path:', filePath);
        console.log('Exists:', existsSync(filePath));

        // Check if file exists
        if (!existsSync(filePath)) {
            return NextResponse.json({
                error: 'File not found',
                path: filePath,
                exists: false
            }, { status: 404 });
        }

        const fileBuffer = await readFile(filePath);

        // Return the PDF file for inline viewing
        return new NextResponse(fileBuffer, {
            headers: {
                'Content-Type': 'application/pdf',
                'Content-Disposition': `inline; filename="${filename}"`,
                'Cache-Control': 'public, max-age=31536000',
            },
        });
    } catch (error: any) {
        console.error('Error serving file:', error);
        return NextResponse.json({ error: 'Error reading file', message: error.message }, { status: 500 });
    }
}
