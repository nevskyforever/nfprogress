import type { ProjectReadRepository } from '@/core/repositories/projects'
import type { Project, ProjectListQuery } from '@/types/api'
import { mapProjects, type SqliteProjectReadModel } from './projectMapper'

interface SqliteBridge {
  readProjects(): Promise<SqliteProjectReadModel>
}

async function bridge(): Promise<SqliteBridge> {
  const { invoke } = await import('@tauri-apps/api/core')
  return { readProjects: () => invoke<SqliteProjectReadModel>('read_sqlite_projects') }
}

export class SQLiteProjectReadRepository implements ProjectReadRepository {
  async listProjects(query: ProjectListQuery = {}): Promise<Project[]> {
    const projects = mapProjects(await (await bridge()).readProjects())
    const search = query.search?.trim().toLocaleLowerCase()
    return projects
      .filter((project) => !query.status || project.status === query.status)
      .filter((project) => !search || project.name.toLocaleLowerCase().includes(search)
        || project.stages.some((stage) => stage.name.toLocaleLowerCase().includes(search)))
      .sort((left, right) => {
        if (query.sort === 'name') return left.name.localeCompare(right.name)
        if (query.sort === 'progress') return right.progress - left.progress
        if (query.sort === 'updated') return (right.updated_at ?? '').localeCompare(left.updated_at ?? '')
        return 0
      })
  }

  async getProject(id: string): Promise<Project | null> {
    const project = mapProjects(await (await bridge()).readProjects()).find((item) => item.id === id)
    return project ?? null
  }
}
