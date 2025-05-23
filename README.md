# Tele Fiocruz


Sistema de teleatendimento em saúde para realização de teleconsultas e teleinterconsultas em várias áreas (medicina, psicologia, fisioterapia etc.) e diversas especialidades. Os teleatendimentos possuem um fluxo completamente digital, uma vez que os termos de consentimento são aceites eletronicamente pelos pacientes e os documentos emitidos são assinados digitalmente pelos profissionais de saúde. Os registros cínicos são realizados através do método SOAP (Subjetivo / Objetivo / Avaliação / Plano) e as estatísticas relacionadas aos atendimentos alimentam automaticamente um painel disponibilizado tanto para os gestores quanto para a comunidade em geral.

## Run

```
./start.sh
```

## Test

```
python manage.py integration_test api.tests.IntegrationTestCase --noinput
```

## Migração

```
python manage.py dumpdata auth.user auth.group comum.perfil

python manage.py dumpdata auth.user comum.CategoriaProfissional comum.CID comum.CIAP comum.TipoEnfoqueResposta comum.AreaTematica comum.TipoSolicitacao comum.UnidadeFederativa comum.NivelFormacao comum.Sexo comum.Municipio comum.EstabelecimentoSaude comum.Especialidade comum.Usuario comum.AnexoUsuario comum.ProfissionalSaude comum.HistoricoAlteracaoProfissional comum.ProfissionalVinculo comum.Solicitacao comum.AnexoSolicitacao comum.StatusSolicitacao comum.FluxoSolicitacao comum.AvaliacaoSolicitacao comum.ProfissionalSaudeRegulador comum.ProfissionalSaudeEspecialista comum.ProfissionalSaudeGestorMunicipio comum.MotivoEncerramentoConferencia comum.CertificadoDigital EncaminhamentosCondutas > dados.json

```

```
Especialidade.objects.filter(profissionalsaude__isnull=True).delete()
```


POSTGRES_DB=telefiocruz
export POSTGRES_HOST=localhost