import mammoth from 'mammoth'
import { Document, Packer, Paragraph, TextRun, HeadingLevel } from 'docx'
import type { TiptapDocument } from '@/types/documents'

export async function importDocx(file: ArrayBuffer): Promise<string> {
  const result = await mammoth.convertToHtml({ arrayBuffer: file }, {
    convertImage: mammoth.images.imgElement((image) => image.read('base64').then((value) => ({ src: `data:${image.contentType};base64,${value}` }))),
  })
  return result.value
}

function runs(node: Record<string, any>): TextRun[] {
  if (node.type === 'text') return [new TextRun({ text: node.text ?? '', bold: node.marks?.some((mark: any) => mark.type === 'bold'), italics: node.marks?.some((mark: any) => mark.type === 'italic'), underline: node.marks?.some((mark: any) => mark.type === 'underline') ? {} : undefined })]
  return (node.content ?? []).flatMap(runs)
}

export async function exportDocx(content: TiptapDocument): Promise<Blob> {
  const children = (content.content ?? []).flatMap((node: Record<string, any>) => {
    if (node.type === 'bulletList' || node.type === 'orderedList') return (node.content ?? []).map((item: Record<string, any>) => new Paragraph({ children: runs(item), bullet: node.type === 'bulletList' ? { level: 0 } : undefined, numbering: node.type === 'orderedList' ? { reference: 'default-numbering', level: 0 } : undefined }))
    if (node.type === 'heading') return [new Paragraph({ children: runs(node), heading: [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][Math.max(0, Math.min(2, (node.attrs?.level ?? 1) - 1))] })]
    if (node.type === 'blockquote') return [new Paragraph({ children: runs(node), indent: { left: 720 }, border: { left: { color: '888888', space: 6, style: 'single', size: 12 } } })]
    if (node.type === 'horizontalRule') return [new Paragraph({ text: '—' })]
    return [new Paragraph({ children: runs(node) })]
  })
  return Packer.toBlob(new Document({ sections: [{ children }], numbering: { config: [{ reference: 'default-numbering', levels: [{ level: 0, format: 'decimal', text: '%1.', alignment: 'left' }] }] } }))
}

export async function blobToBase64(blob: Blob): Promise<string> {
  const data = new Uint8Array(await blob.arrayBuffer()); let binary = ''
  for (const byte of data) binary += String.fromCharCode(byte)
  return btoa(binary)
}
